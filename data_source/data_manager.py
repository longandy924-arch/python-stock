"""统一数据管理层。

当前能力：
1. 历史数据 Provider 可插拔
2. Tushare 历史数据
3. 本地 CSV 缓存
4. 为后续实时行情 Provider 预留标准接口
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from data_source.providers import (
    DataProviderError,
    HistoricalDataProvider,
    TushareProvider,
)


class DataManagerError(RuntimeError):
    """统一数据管理异常。"""


def build_historical_provider(
    provider_name: str,
) -> HistoricalDataProvider:
    """根据名称创建历史数据 Provider。"""

    providers: dict[str, type[HistoricalDataProvider]] = {
        "tushare": TushareProvider,
    }

    provider_class = providers.get(provider_name.lower())

    if provider_class is None:
        supported = ", ".join(sorted(providers))
        raise DataManagerError(
            f"不支持的数据源：{provider_name}；当前支持：{supported}"
        )

    return provider_class()


@dataclass
class DataManager:
    """为策略、回测和实盘提供统一数据入口。"""

    primary_source: str = "tushare"
    cache_dir: Path | str = field(
        default_factory=lambda: Path("data/cache")
    )
    enable_cache: bool = True
    provider: HistoricalDataProvider | None = None

    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if self.provider is None:
            self.provider = build_historical_provider(
                self.primary_source
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
        return self.cache_dir / (
            f"daily_{safe_code}_{start_date}_{end_date}.csv"
        )

    @staticmethod
    def _read_csv(path: Path) -> pd.DataFrame:
        try:
            df = pd.read_csv(path, dtype={"trade_date": str})
        except Exception as exc:
            raise DataManagerError(
                f"读取缓存失败：{path}，{exc}"
            ) from exc

        if df.empty:
            raise DataManagerError(f"缓存文件为空：{path}")

        return df

    @staticmethod
    def _write_csv(df: pd.DataFrame, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            df.to_csv(path, index=False, encoding="utf-8-sig")
        except Exception as exc:
            raise DataManagerError(
                f"写入缓存失败：{path}，{exc}"
            ) from exc

    def get_stock_list(
        self,
        list_status: str = "L",
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        cache_path = self._stock_list_cache_path(list_status)

        if (
            self.enable_cache
            and cache_path.exists()
            and not force_refresh
        ):
            return self._read_csv(cache_path)

        try:
            df = self.provider.get_stock_list(
                list_status=list_status
            )
        except DataProviderError as exc:
            if self.enable_cache and cache_path.exists():
                print(f"数据源失败，改用旧缓存：{exc}")
                return self._read_csv(cache_path)

            raise DataManagerError(
                f"股票列表获取失败：{exc}"
            ) from exc

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
        cache_path = self._daily_cache_path(
            ts_code,
            start_date,
            end_date,
        )

        if (
            self.enable_cache
            and cache_path.exists()
            and not force_refresh
        ):
            return self._read_csv(cache_path)

        try:
            df = self.provider.get_daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
        except DataProviderError as exc:
            if self.enable_cache and cache_path.exists():
                print(f"数据源失败，改用旧缓存：{exc}")
                return self._read_csv(cache_path)

            raise DataManagerError(
                f"{ts_code}日线数据获取失败：{exc}"
            ) from exc

        if self.enable_cache:
            self._write_csv(df, cache_path)

        return df

    def clear_cache(self) -> int:
        deleted = 0

        for path in self.cache_dir.glob("*.csv"):
            path.unlink()
            deleted += 1

        return deleted
