"""统一数据层真实连接及缓存验证。"""

from pathlib import Path
import tempfile

from data_source.data_manager import DataManager


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)

        manager = DataManager(cache_dir=cache_dir)

        first = manager.get_daily(
            ts_code="000001.SZ",
            start_date="20260701",
            end_date="20260728",
            force_refresh=True,
        )

        cache_files = list(cache_dir.glob("daily_*.csv"))

        assert not first.empty
        assert len(cache_files) == 1

        second = manager.get_daily(
            ts_code="000001.SZ",
            start_date="20260701",
            end_date="20260728",
        )

        assert len(first) == len(second)
        assert first["trade_date"].astype(str).tolist() == (
            second["trade_date"].astype(str).tolist()
        )

        print("DataManager真实数据读取成功")
        print("本地CSV缓存写入成功")
        print("本地CSV缓存读取成功")
        print(f"测试数据：{len(second)} 条")
