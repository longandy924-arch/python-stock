"""Provider 架构真实验证。"""

from pathlib import Path
import tempfile

from data_source.data_manager import DataManager
from data_source.providers import (
    HistoricalDataProvider,
    TushareProvider,
)


if __name__ == "__main__":
    provider = TushareProvider()

    assert isinstance(provider, HistoricalDataProvider)
    assert provider.provider_name == "tushare"

    with tempfile.TemporaryDirectory() as temp_dir:
        manager = DataManager(
            provider=provider,
            cache_dir=Path(temp_dir),
        )

        daily = manager.get_daily(
            ts_code="000001.SZ",
            start_date="20260701",
            end_date="20260728",
            force_refresh=True,
        )

        assert not daily.empty
        assert {"trade_date", "open", "high", "low", "close"}.issubset(
            daily.columns
        )

        cached = manager.get_daily(
            ts_code="000001.SZ",
            start_date="20260701",
            end_date="20260728",
        )

        assert len(daily) == len(cached)

    print("Provider标准接口验证成功")
    print("TushareProvider真实数据验证成功")
    print("DataManager Provider注入验证成功")
    print("CSV缓存兼容验证成功")
