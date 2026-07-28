"""Tushare 数据接口封装。"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd
import tushare as ts


class TushareConfigError(RuntimeError):
    """Tushare 配置错误。"""


class TushareDataError(RuntimeError):
    """Tushare 数据获取错误。"""


@dataclass
class TushareAPI:
    """统一封装 Tushare Pro 数据接口。"""

    token: str | None = None

    def __post_init__(self) -> None:
        self.token = self.token or os.getenv("TUSHARE_TOKEN")

        if not self.token:
            raise TushareConfigError(
                "未读取到 TUSHARE_TOKEN，请先配置本机环境变量。"
            )

        self.pro = ts.pro_api(self.token)

    def get_stock_list(self, list_status: str = "L") -> pd.DataFrame:
        """获取当前上市股票基础信息。"""
        try:
            df = self.pro.stock_basic(
                exchange="",
                list_status=list_status,
                fields=(
                    "ts_code,symbol,name,area,industry,market,"
                    "exchange,list_status,list_date"
                ),
            )
        except Exception as exc:
            raise TushareDataError(f"获取股票列表失败：{exc}") from exc

        if df.empty:
            raise TushareDataError("股票列表为空。")

        return df.sort_values("ts_code").reset_index(drop=True)

    def get_daily(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """获取单只股票日线行情，日期格式为 YYYYMMDD。"""
        if not ts_code:
            raise ValueError("ts_code 不能为空。")

        if len(start_date) != 8 or len(end_date) != 8:
            raise ValueError("start_date 和 end_date 必须为 YYYYMMDD 格式。")

        try:
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as exc:
            raise TushareDataError(f"获取 {ts_code} 日线数据失败：{exc}") from exc

        if df.empty:
            raise TushareDataError(
                f"{ts_code} 在 {start_date} 至 {end_date} 没有返回日线数据。"
            )

        df = df.sort_values("trade_date").reset_index(drop=True)

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "pre_close",
            "change",
            "pct_chg",
            "vol",
            "amount",
        ]

        for column in numeric_columns:
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors="coerce")

        return df


if __name__ == "__main__":
    api = TushareAPI()

    stocks = api.get_stock_list()
    print(f"股票列表读取成功：{len(stocks)} 只")
    print(stocks.head(5).to_string(index=False))

    daily = api.get_daily(
        ts_code="000001.SZ",
        start_date="20260701",
        end_date="20260728",
    )
    print(f"\n日线数据读取成功：{len(daily)} 条")
    print(daily.tail(5).to_string(index=False))
