"""Realtime Gateway V1.

This module adds a small provider chain for realtime quotes without changing
strategy-facing APIs.  The gateway always returns a DataFrame with the same
columns and records provider failures in logs/realtime.log.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from data_source.eastmoney_api import EastMoneyAPI
from data_source.providers import RealtimeDataProvider


REQUIRED_COLUMNS = [
    "ts_code",
    "name",
    "price",
    "pct_chg",
    "open",
    "high",
    "low",
    "pre_close",
    "volume",
    "amount",
    "bid1",
    "ask1",
    "bid1_volume",
    "ask1_volume",
    "update_time",
]

NUMERIC_COLUMNS = [
    "price",
    "pct_chg",
    "open",
    "high",
    "low",
    "pre_close",
    "volume",
    "amount",
    "bid1",
    "ask1",
    "bid1_volume",
    "ask1_volume",
]


class RealtimeGatewayError(RuntimeError):
    """Realtime gateway error."""


def build_realtime_logger(log_path: Path | str = "logs/realtime.log") -> logging.Logger:
    """Build a file logger for realtime provider exceptions."""

    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("realtime_gateway")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    resolved_path = str(path.resolve())
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == resolved_path:
            return logger

    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    )
    logger.addHandler(handler)
    return logger


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _empty_quotes() -> pd.DataFrame:
    return pd.DataFrame(columns=REQUIRED_COLUMNS)


def normalize_realtime_quotes(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize provider output to the Realtime Gateway V1 schema."""

    if df is None or df.empty:
        return _empty_quotes()

    result = df.copy()

    rename_map = {
        "代码": "symbol",
        "名称": "name",
        "最新价": "price",
        "涨跌幅": "pct_chg",
        "今开": "open",
        "最高": "high",
        "最低": "low",
        "昨收": "pre_close",
        "成交量": "volume",
        "成交额": "amount",
        "买一": "bid1",
        "卖一": "ask1",
        "买一量": "bid1_volume",
        "卖一量": "ask1_volume",
    }
    result = result.rename(columns=rename_map)

    if "ts_code" not in result.columns and "symbol" in result.columns:
        result["ts_code"] = result["symbol"].map(to_ts_code)

    for column in REQUIRED_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA

    if result["update_time"].isna().all():
        result["update_time"] = _now_text()

    result["ts_code"] = result["ts_code"].astype(str).str.strip()
    result["name"] = result["name"].astype(str).str.strip()

    for column in NUMERIC_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    result = result[REQUIRED_COLUMNS]
    result = result.dropna(subset=["ts_code", "name"])
    result = result[result["ts_code"] != ""]
    result = result.drop_duplicates(subset=["ts_code"], keep="first")
    result = result.sort_values("ts_code").reset_index(drop=True)

    return result


def to_ts_code(symbol: Any) -> str:
    """Convert symbol formats such as sz000001 or 000001 to ts_code."""

    text = str(symbol).strip().upper()
    if "." in text:
        code, suffix = text.split(".", 1)
        return f"{code.zfill(6)}.{suffix}"
    if text.startswith(("SH", "SZ", "BJ")):
        prefix = text[:2]
        code = text[2:].zfill(6)
        return f"{code}.{prefix}"

    code = text.zfill(6)
    if code.startswith("6"):
        return f"{code}.SH"
    if code.startswith(("0", "3")):
        return f"{code}.SZ"
    if code.startswith(("4", "8", "9")):
        return f"{code}.BJ"
    return code


def to_tencent_code(ts_code: Any) -> str:
    """Convert ts_code to Tencent quote code."""

    text = str(ts_code).strip().upper()
    code = text.split(".", 1)[0].zfill(6)
    suffix = text.split(".", 1)[1] if "." in text else ""

    if suffix == "SH" or code.startswith("6"):
        return f"sh{code}"
    if suffix == "BJ" or code.startswith(("4", "8", "9")):
        return f"bj{code}"
    return f"sz{code}"


class EastMoneyRealtimeProvider(RealtimeDataProvider):
    """EastMoney realtime provider."""

    provider_name = "eastmoney"

    def __init__(self, api: EastMoneyAPI | None = None) -> None:
        self.api = api or EastMoneyAPI(page_size=100)

    def is_available(self) -> bool:
        return True

    def get_quotes(self) -> pd.DataFrame:
        return normalize_realtime_quotes(self.api.get_realtime_quotes())


class TencentRealtimeProvider(RealtimeDataProvider):
    """Tencent quote provider for a seed list of symbols."""

    provider_name = "tencent"

    def __init__(
        self,
        ts_codes: list[str] | None = None,
        timeout: float = 8.0,
        session: Any | None = None,
    ) -> None:
        self.ts_codes = ts_codes or ["000001.SZ"]
        self.timeout = timeout
        self.session = session or requests.Session()

    def is_available(self) -> bool:
        return bool(self.ts_codes)

    def get_quotes(self) -> pd.DataFrame:
        codes = ",".join(to_tencent_code(ts_code) for ts_code in self.ts_codes)
        response = self.session.get(
            "https://qt.gtimg.cn/q=" + codes,
            timeout=self.timeout,
        )
        response.raise_for_status()

        rows = []
        for line in response.text.splitlines():
            if not line or '="' not in line:
                continue

            raw_code = line.split("=", 1)[0].replace("v_", "")
            payload = line.split('="', 1)[1].rstrip('";')
            parts = payload.split("~")
            if len(parts) < 50:
                continue

            rows.append(
                {
                    "ts_code": to_ts_code(raw_code),
                    "name": parts[1],
                    "price": parts[3],
                    "pct_chg": parts[32],
                    "volume": parts[36],
                    "amount": parts[37],
                    "bid1": parts[9],
                    "ask1": parts[19],
                    "bid1_volume": parts[10],
                    "ask1_volume": parts[20],
                    "update_time": parts[30] or _now_text(),
                }
            )

        return normalize_realtime_quotes(pd.DataFrame(rows))


class AKShareRealtimeProvider(RealtimeDataProvider):
    """AKShare realtime quote provider."""

    provider_name = "akshare"

    def __init__(self, akshare_module: Any | None = None) -> None:
        self.akshare_module = akshare_module

    def is_available(self) -> bool:
        if self.akshare_module is not None:
            return True

        try:
            import akshare as akshare_module
        except Exception:
            return False

        self.akshare_module = akshare_module
        return True

    def get_quotes(self) -> pd.DataFrame:
        if not self.is_available():
            return _empty_quotes()

        df = self.akshare_module.stock_zh_a_spot_em()
        return normalize_realtime_quotes(df)


class LocalCacheRealtimeProvider(RealtimeDataProvider):
    """Local CSV cache provider used as the last fallback."""

    provider_name = "local_cache"

    def __init__(self, cache_path: Path | str = "data/cache/realtime_quotes.csv") -> None:
        self.cache_path = Path(cache_path)

    def is_available(self) -> bool:
        return self.cache_path.exists() and self.cache_path.stat().st_size > 0

    def get_quotes(self) -> pd.DataFrame:
        df = pd.read_csv(self.cache_path, dtype={"ts_code": str})
        return normalize_realtime_quotes(df)

    def save_quotes(self, df: pd.DataFrame) -> None:
        quotes = normalize_realtime_quotes(df)
        if quotes.empty:
            return

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        quotes.to_csv(self.cache_path, index=False, encoding="utf-8-sig")


@dataclass
class RealtimeGateway:
    """Realtime quote gateway with provider failover."""

    providers: list[RealtimeDataProvider] | None = None
    cache_path: Path | str = "data/cache/realtime_quotes.csv"
    log_path: Path | str = "logs/realtime.log"
    current_source: str | None = None
    response_time_ms: float = 0.0
    stock_count: int = 0
    switched: bool = False
    logger: logging.Logger = field(init=False)

    def __post_init__(self) -> None:
        self.logger = build_realtime_logger(self.log_path)
        self.cache_provider = LocalCacheRealtimeProvider(self.cache_path)

        if self.providers is None:
            self.providers = [
                EastMoneyRealtimeProvider(),
                TencentRealtimeProvider(),
                AKShareRealtimeProvider(),
                self.cache_provider,
            ]

    def _record_result(
        self,
        provider: RealtimeDataProvider | None,
        quotes: pd.DataFrame,
        started_at: float,
        provider_index: int | None,
    ) -> pd.DataFrame:
        self.current_source = provider.provider_name if provider else None
        self.response_time_ms = round((time.perf_counter() - started_at) * 1000, 2)
        self.stock_count = len(quotes)
        self.switched = bool(provider_index and provider_index > 0)
        return quotes

    def get_realtime_quotes(self) -> pd.DataFrame:
        """Return realtime quotes using EastMoney, Tencent, AKShare, then cache."""

        started_at = time.perf_counter()

        for index, provider in enumerate(self.providers or []):
            try:
                if not provider.is_available():
                    self.logger.warning(
                        "%s unavailable, skipped", provider.provider_name
                    )
                    continue
            except Exception:
                self.logger.exception(
                    "%s availability check failed", provider.provider_name
                )
                continue

            try:
                quotes = normalize_realtime_quotes(provider.get_quotes())
                if quotes.empty:
                    raise RealtimeGatewayError(
                        f"{provider.provider_name} returned empty quotes"
                    )

                if provider.provider_name != self.cache_provider.provider_name:
                    self.cache_provider.save_quotes(quotes)

                return self._record_result(
                    provider=provider,
                    quotes=quotes,
                    started_at=started_at,
                    provider_index=index,
                )
            except Exception:
                self.logger.exception("%s get_quotes failed", provider.provider_name)

        empty = _empty_quotes()
        return self._record_result(
            provider=None,
            quotes=empty,
            started_at=started_at,
            provider_index=None,
        )


_DEFAULT_GATEWAY: RealtimeGateway | None = None


def get_realtime_quotes() -> pd.DataFrame:
    """Module-level realtime quote entry point."""

    global _DEFAULT_GATEWAY
    if _DEFAULT_GATEWAY is None:
        _DEFAULT_GATEWAY = RealtimeGateway()
    return _DEFAULT_GATEWAY.get_realtime_quotes()


if __name__ == "__main__":
    gateway = RealtimeGateway()
    quotes = gateway.get_realtime_quotes()
    print(f"当前使用的数据源：{gateway.current_source}")
    print(f"响应时间(ms)：{gateway.response_time_ms}")
    print(f"返回股票数量：{gateway.stock_count}")
    print(f"是否自动切换成功：{gateway.switched}")
    print(quotes.head(5).to_string(index=False))
