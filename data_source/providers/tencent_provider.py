"""腾讯实时行情 Provider。

功能：
1. 支持 Tushare 格式股票代码；
2. 支持分批获取腾讯实时行情；
3. 输出 Realtime Gateway 统一字段；
4. 网络异常统一抛出 DataProviderError。
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

import pandas as pd
from curl_cffi import requests

from data_source.providers.base import (
    DataProviderError,
    RealtimeDataProvider,
)


REQUIRED_COLUMNS = [
    "ts_code",
    "name",
    "price",
    "pct_chg",
    "volume",
    "amount",
    "bid1",
    "ask1",
    "bid1_volume",
    "ask1_volume",
    "update_time",
]


def _empty_quotes() -> pd.DataFrame:
    return pd.DataFrame(columns=REQUIRED_COLUMNS)


def _to_tencent_code(ts_code: str) -> str:
    text = str(ts_code).strip().upper()
    code = text.split(".", 1)[0].zfill(6)
    suffix = text.split(".", 1)[1] if "." in text else ""

    if suffix == "SH" or code.startswith("6"):
        return f"sh{code}"

    if suffix == "BJ" or code.startswith(("4", "8", "9")):
        return f"bj{code}"

    return f"sz{code}"


def _to_ts_code(tencent_code: str) -> str:
    text = str(tencent_code).strip().lower()
    prefix = text[:2]
    code = text[2:].zfill(6)

    suffix_map = {
        "sh": "SH",
        "sz": "SZ",
        "bj": "BJ",
    }

    suffix = suffix_map.get(prefix)
    return f"{code}.{suffix}" if suffix else code


def _safe_float(value: object) -> float | None:
    try:
        text = str(value).strip()
        if not text or text in {"--", "None", "nan"}:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index:index + size]


class TencentRealtimeProvider(RealtimeDataProvider):
    """腾讯实时行情数据源。"""

    provider_name = "tencent"

    def __init__(
        self,
        ts_codes: list[str] | None = None,
        timeout: float = 10.0,
        batch_size: int = 60,
    ) -> None:
        self.ts_codes = ts_codes or ["000001.SZ"]
        self.timeout = timeout
        self.batch_size = batch_size

    def is_available(self) -> bool:
        return bool(self.ts_codes)

    def _request_batch(self, ts_codes: list[str]) -> str:
        symbols = ",".join(
            _to_tencent_code(ts_code)
            for ts_code in ts_codes
        )

        url = f"https://qt.gtimg.cn/q={symbols}"

        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                impersonate="safari",
            )
            response.raise_for_status()
        except Exception as exc:
            raise DataProviderError(
                f"腾讯实时行情请求失败：{exc}"
            ) from exc

        if not response.text.strip():
            raise DataProviderError("腾讯实时行情返回空内容。")

        return response.text

    @staticmethod
    def _parse_response(text: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []

        for line in text.splitlines():
            if '="' not in line:
                continue

            variable, payload = line.split('="', 1)
            raw_code = variable.replace("v_", "").strip()
            payload = payload.rstrip('";\r\n')
            parts = payload.split("~")

            if len(parts) < 38:
                continue

            name = parts[1].strip()
            price = _safe_float(parts[3])

            if not name or price is None:
                continue

            raw_time = parts[30].strip() if len(parts) > 30 else ""
            update_time = raw_time or datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            rows.append(
                {
                    "ts_code": _to_ts_code(raw_code),
                    "name": name,
                    "price": price,
                    "pct_chg": _safe_float(parts[32]),
                    "volume": _safe_float(parts[36]),
                    "amount": _safe_float(parts[37]),
                    "bid1": _safe_float(parts[9]),
                    "ask1": _safe_float(parts[19]),
                    "bid1_volume": _safe_float(parts[10]),
                    "ask1_volume": _safe_float(parts[20]),
                    "update_time": update_time,
                }
            )

        return rows

    def get_quotes(self) -> pd.DataFrame:
        if not self.is_available():
            raise DataProviderError("腾讯 Provider 没有股票代码。")

        all_rows: list[dict[str, object]] = []

        for batch in _chunks(self.ts_codes, self.batch_size):
            text = self._request_batch(batch)
            all_rows.extend(self._parse_response(text))

        if not all_rows:
            raise DataProviderError("腾讯实时行情解析后为空。")

        result = pd.DataFrame(all_rows)

        for column in REQUIRED_COLUMNS:
            if column not in result.columns:
                result[column] = pd.NA

        result = result[REQUIRED_COLUMNS]
        result = result.drop_duplicates(
            subset=["ts_code"],
            keep="first",
        )
        result = result.sort_values("ts_code").reset_index(drop=True)

        return result
