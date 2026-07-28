"""Tushare 历史数据 Provider。"""

from __future__ import annotations

import pandas as pd

from data_source.providers.base import (
    DataProviderError,
    HistoricalDataProvider,
)
from data_source.tushare_api import TushareAPI, TushareDataError


class TushareProvider(HistoricalDataProvider):
    """将现有 TushareAPI 接入统一 Provider 接口。"""

    provider_name = "tushare"

    def __init__(self, token: str | None = None) -> None:
        self.api = TushareAPI(token=token)

    def get_stock_list(self, list_status: str = "L") -> pd.DataFrame:
        try:
            return self.api.get_stock_list(list_status=list_status)
        except TushareDataError as exc:
            raise DataProviderError(
                f"Tushare股票列表获取失败：{exc}"
            ) from exc

    def get_daily(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        try:
            return self.api.get_daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
        except TushareDataError as exc:
            raise DataProviderError(
                f"Tushare日线数据获取失败：{exc}"
            ) from exc
