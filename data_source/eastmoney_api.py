"""EastMoney realtime quote interface.

The client talks to EastMoney's public JSON endpoint directly instead of
delegating realtime quotes to AKShare.  AKShare is still useful elsewhere, but
its paginated wrapper can fail the whole request when EastMoney closes one HTTP
connection.  Here each page is retried independently and alternate hosts are
tried before surfacing a data error.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, ClassVar

import pandas as pd
import requests

try:
    from curl_cffi import requests as curl_requests
    from curl_cffi.requests.exceptions import RequestException as CurlRequestError
except Exception:  # pragma: no cover - requests fallback is covered in tests.
    curl_requests = None
    CurlRequestError = requests.RequestException


class EastMoneyDataError(RuntimeError):
    """Raised when EastMoney data cannot be fetched or parsed."""


@dataclass
class EastMoneyAPI:
    """Fetch and normalize A-share realtime quotes from EastMoney."""

    timeout: float = 8.0
    page_size: int = 200
    max_pages: int = 80
    retries: int = 3
    backoff: float = 0.3
    use_env_proxy: bool = False
    session: Any | None = None
    hosts: tuple[str, ...] = (
        "push2delay.eastmoney.com",
        "82.push2.eastmoney.com",
        "83.push2.eastmoney.com",
        "push2.eastmoney.com",
    )

    ENDPOINT_PATH: ClassVar[str] = "/api/qt/clist/get"
    FS_FILTER: ClassVar[str] = (
        "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048"
    )
    FIELDS: ClassVar[tuple[str, ...]] = (
        "f2",
        "f3",
        "f4",
        "f5",
        "f6",
        "f7",
        "f8",
        "f9",
        "f10",
        "f11",
        "f12",
        "f14",
        "f15",
        "f16",
        "f17",
        "f18",
        "f20",
        "f21",
        "f22",
        "f24",
        "f25",
    )
    COLUMN_MAP: ClassVar[dict[str, str]] = {
        "f12": "symbol",
        "f14": "name",
        "f2": "price",
        "f4": "change",
        "f3": "pct_chg",
        "f17": "open",
        "f15": "high",
        "f16": "low",
        "f18": "pre_close",
        "f5": "volume",
        "f6": "amount",
        "f7": "amplitude",
        "f8": "turnover_rate",
        "f10": "volume_ratio",
        "f9": "pe_dynamic",
        "f20": "total_mv",
        "f21": "circ_mv",
        "f22": "speed",
        "f11": "pct_chg_5m",
        "f24": "pct_chg_60d",
        "f25": "pct_chg_ytd",
    }
    NUMERIC_COLUMNS: ClassVar[tuple[str, ...]] = (
        "price",
        "change",
        "pct_chg",
        "open",
        "high",
        "low",
        "pre_close",
        "volume",
        "amount",
        "amplitude",
        "turnover_rate",
        "volume_ratio",
        "pe_dynamic",
        "total_mv",
        "circ_mv",
        "speed",
        "pct_chg_5m",
        "pct_chg_60d",
        "pct_chg_ytd",
    )
    OUTPUT_COLUMNS: ClassVar[tuple[str, ...]] = (
        "ts_code",
        "symbol",
        "name",
        "price",
        "change",
        "pct_chg",
        "open",
        "high",
        "low",
        "pre_close",
        "volume",
        "amount",
        "amplitude",
        "turnover_rate",
        "volume_ratio",
        "pe_dynamic",
        "total_mv",
        "circ_mv",
        "speed",
        "pct_chg_5m",
        "pct_chg_60d",
        "pct_chg_ytd",
    )

    def __post_init__(self) -> None:
        if self.page_size <= 0:
            raise ValueError("page_size 必须大于 0。")
        if self.max_pages <= 0:
            raise ValueError("max_pages 必须大于 0。")
        if self.retries <= 0:
            raise ValueError("retries 必须大于 0。")
        if not self.hosts:
            raise ValueError("hosts 不能为空。")

        if self.session is None:
            if curl_requests is not None:
                self.session = curl_requests.Session(impersonate="chrome")
            else:
                self.session = requests.Session()

            if hasattr(self.session, "trust_env"):
                self.session.trust_env = self.use_env_proxy
            self.session.headers.update(
                {
                    "Accept": "application/json, text/plain, */*",
                    "Connection": "close",
                    "Referer": "https://quote.eastmoney.com/",
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0 Safari/537.36"
                    ),
                }
            )

    @staticmethod
    def _to_ts_code(symbol: str) -> str:
        """Convert an EastMoney symbol to Tushare-style ts_code."""

        raw = str(symbol).strip().upper()
        if "." in raw:
            code, suffix = raw.split(".", 1)
            return f"{code.zfill(6)}.{suffix}"

        code = raw.zfill(6)
        if code.startswith("6"):
            return f"{code}.SH"
        if code.startswith(("0", "3")):
            return f"{code}.SZ"
        if code.startswith(("4", "8", "9")):
            return f"{code}.BJ"
        return code

    @staticmethod
    def _to_symbol(ts_code: str) -> str:
        """Return the six-digit stock symbol from a symbol or ts_code."""

        return str(ts_code).strip().upper().split(".", 1)[0].zfill(6)

    def _params(self, page: int) -> dict[str, Any]:
        return {
            "pn": page,
            "pz": self.page_size,
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f12",
            "fs": self.FS_FILTER,
            "fields": ",".join(self.FIELDS),
        }

    def _request_json(self, page: int) -> dict[str, Any]:
        last_error: Exception | None = None
        params = self._params(page)

        for attempt in range(1, self.retries + 1):
            for host in self.hosts:
                url = f"https://{host}{self.ENDPOINT_PATH}"
                try:
                    response = self.session.get(
                        url,
                        params=params,
                        timeout=self.timeout,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise EastMoneyDataError("东方财富返回内容不是 JSON 对象。")
                    return payload
                except (
                    requests.RequestException,
                    CurlRequestError,
                    ValueError,
                    EastMoneyDataError,
                ) as exc:
                    last_error = exc

            if attempt < self.retries and self.backoff > 0:
                time.sleep(self.backoff * attempt)

        raise EastMoneyDataError(
            f"东方财富第 {page} 页行情请求失败：{last_error}"
        ) from last_error

    def _fetch_page(self, page: int) -> tuple[list[dict[str, Any]], int]:
        payload = self._request_json(page)
        data = payload.get("data")

        if not isinstance(data, dict):
            raise EastMoneyDataError("东方财富返回缺少 data 字段。")

        diff = data.get("diff") or []
        total = int(data.get("total") or 0)

        if not isinstance(diff, list):
            raise EastMoneyDataError("东方财富返回 diff 字段格式异常。")

        return diff, total

    def _normalize(self, rows: list[dict[str, Any]]) -> pd.DataFrame:
        if not rows:
            raise EastMoneyDataError("东方财富实时行情为空。")

        df = pd.DataFrame(rows).rename(columns=self.COLUMN_MAP)
        missing = {"symbol", "name"} - set(df.columns)
        if missing:
            raise EastMoneyDataError(f"东方财富返回缺少字段：{sorted(missing)}")

        result = df.copy()
        result["symbol"] = (
            result["symbol"].astype(str).str.strip().str.zfill(6)
        )
        result["ts_code"] = result["symbol"].map(self._to_ts_code)
        result = result.replace({"-": pd.NA, "": pd.NA})

        for column in self.NUMERIC_COLUMNS:
            if column in result.columns:
                result[column] = pd.to_numeric(result[column], errors="coerce")

        existing_columns = [
            column for column in self.OUTPUT_COLUMNS if column in result.columns
        ]
        result = result[existing_columns]
        result = result.dropna(subset=["symbol", "name"])
        result = result.drop_duplicates(subset=["ts_code"], keep="first")
        result = result.sort_values("ts_code").reset_index(drop=True)

        if result.empty:
            raise EastMoneyDataError("东方财富实时行情清洗后为空。")

        return result

    def get_realtime_quotes(self) -> pd.DataFrame:
        """Fetch realtime quotes for all A-share stocks."""

        all_rows: list[dict[str, Any]] = []
        total = 0

        for page in range(1, self.max_pages + 1):
            rows, total = self._fetch_page(page)
            if not rows:
                break

            all_rows.extend(rows)
            if total and len(all_rows) >= total:
                break

        if total and len(all_rows) < total:
            raise EastMoneyDataError(
                f"东方财富行情分页不完整：已获取 {len(all_rows)} / {total}。"
            )

        return self._normalize(all_rows)

    def get_quote(self, ts_code: str) -> pd.Series:
        """Fetch one stock quote from the full realtime quote table."""

        symbol = self._to_symbol(ts_code)
        quotes = self.get_realtime_quotes()
        matched = quotes.loc[quotes["symbol"] == symbol]

        if matched.empty:
            raise EastMoneyDataError(f"未找到 {ts_code} 的东方财富实时行情。")

        return matched.iloc[0]


if __name__ == "__main__":
    api = EastMoneyAPI()
    quotes = api.get_realtime_quotes()
    print(f"东方财富实时行情读取成功：{len(quotes)} 只")
    print(quotes.head(5).to_string(index=False))

    quote = api.get_quote("000001.SZ")
    print("\n000001.SZ 实时行情：")
    print(quote.to_string())
