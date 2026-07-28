"""统一数据源接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class DataProviderError(RuntimeError):
    """数据提供者统一异常。"""


class HistoricalDataProvider(ABC):
    """历史数据源标准接口。"""

    provider_name: str = "unknown"

    @abstractmethod
    def get_stock_list(self, list_status: str = "L") -> pd.DataFrame:
        """获取股票基础列表。"""

    @abstractmethod
    def get_daily(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """获取单只股票日线行情。"""


class RealtimeDataProvider(ABC):
    """实时行情数据源标准接口。"""

    provider_name: str = "unknown"

    @abstractmethod
    def get_realtime_quotes(
        self,
        ts_codes: list[str] | None = None,
    ) -> pd.DataFrame:
        """获取实时行情。"""
