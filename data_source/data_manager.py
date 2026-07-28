"""统一数据管理层。

当前支持：
1. Tushare 数据源
2. 本地 CSV 缓存

后续可在不修改策略层的情况下增加东方财富、腾讯等数据源。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import pandas as pd

from data_source.tushare_api import TushareAPI, TushareDataError


DataSourceName = Literal["tushare"]


class DataManagerError(RuntimeError):
    """统一数据管理异常。"""


@dataclass
class DataManager:
    """为策略、回测和实盘提供统一数据入口。"""

    primary_source: DataSourceName = "tushare"
    cache_dir: Path | str = field(default_factory=lambda: Path("data/cache"))
    enable_cache: bool = True

    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if self.primary_source == "tushare":
            self.provider = TushareAPI()
        else:
            raise DataManagerError(
                f"暂不支持的数据源：{self.primary_source}"
            )

    def _stock_list_cache_path(self, list_status: str) -> Path:
        return self.cache_dir / f"stock_list_{list_status}.csv"

    def _daily_cache_path(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> Path:
        safe_code = ts_code.replace(".", "_")
        filename = f"daily_{safe_code}_{start_date}_{end_date}.csv"
        return self.cache_dir / filename

    @staticmethod
    def _read_csv(path: Path) -> pd.DataFrame:
        try:
            df = pd.read_csv(path, dtype={"trade_date": str})
        except Exception as exc:
            raise DataManagerError(f"读取缓存失败：{path}，{exc}") from exc

        if df.empty:
            raise DataManagerError(f"缓存文件为空：{path}")

        return df

    @staticmethod
    def _write_csv(df: pd.DataFrame, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            df.to_csv(path, index=False, encoding="utf-8-sig")
        except Exception as exc:
            raise DataManagerError(f"写入缓存失败：{path}，{exc}") from exc

    def get_stock_list(
        self,
        list_status: str = "L",
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """获取股票列表。优先缓存，必要时请求 Tushare。"""

        cache_path = self._stock_list_cache_path(list_status)

        if self.enable_cache and cache_path.exists() and not force_refresh:
            return self._read_csv(cache_path)

        try:
            df = self.provider.get_stock_list(list_status=list_status)
        except TushareDataError as exc:
            if self.enable_cache and cache_path.exists():
                print(f"数据源请求失败，改用旧缓存：{exc}")
                return self._read_csv(cache_path)

            raise DataManagerError(f"股票列表获取失败：{exc}") from exc

        if self.enable_cache:
            self._write_csv(df, cache_path)

        return df

    def get_daily(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """获取单只股票日线行情。"""

        cache_path = self._daily_cache_path(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )

        if self.enable_cache and cache_path.exists() and not force_refresh:
            return self._read_csv(cache_path)

        try:
            df = self.provider.get_daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
        except TushareDataError as exc:
            if self.enable_cache and cache_path.exists():
                print(f"数据源请求失败，改用旧缓存：{exc}")
                return self._read_csv(cache_path)

            raise DataManagerError(
                f"{ts_code} 日线数据获取失败：{exc}"
            ) from exc

        if self.enable_cache:
            self._write_csv(df, cache_path)

        return df

    def clear_cache(self) -> int:
        """清理当前数据缓存，返回删除文件数量。"""

        deleted = 0

        for path in self.cache_dir.glob("*.csv"):
            path.unlink()
            deleted += 1

        return deleted


if __name__ == "__main__":
    manager = DataManager()

    stocks = manager.get_stock_list()
    print(f"统一数据层股票列表：{len(stocks)} 只")

    daily = manager.get_daily(
        ts_code="000001.SZ",
        start_date="20260701",
        end_date="20260728",
    )
    print(f"统一数据层日线数据：{len(daily)} 条")
    print(daily.tail(3).to_string(index=False))
