"""14:55实时快照采集器基础验证。"""

from pathlib import Path
import tempfile

import pandas as pd

from realtime.collect_1455 import (
    SnapshotValidationError,
    save_snapshot,
    validate_snapshot,
)


class FakeGateway:
    current_source = "fake_full_market"
    response_time_ms = 120.5


def build_quotes(count: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ts_code": [
                f"{index:06d}.SZ"
                for index in range(count)
            ],
            "name": [
                f"测试股票{index}"
                for index in range(count)
            ],
            "price": [10.0] * count,
            "pct_chg": [0.5] * count,
            "volume": [100000.0] * count,
            "amount": [1000000.0] * count,
            "bid1": [9.99] * count,
            "ask1": [10.01] * count,
            "bid1_volume": [1000.0] * count,
            "ask1_volume": [1200.0] * count,
            "update_time": [
                "2026-07-28 14:55:00"
            ] * count,
        }
    )


if __name__ == "__main__":
    valid = validate_snapshot(
        build_quotes(5100),
        minimum_stock_count=5000,
    )
    assert len(valid) == 5100

    try:
        validate_snapshot(
            build_quotes(3),
            minimum_stock_count=5000,
        )
    except SnapshotValidationError:
        pass
    else:
        raise AssertionError(
            "残缺行情未被正确拦截"
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        metadata = save_snapshot(
            valid,
            gateway=FakeGateway(),
            output_root=Path(temp_dir),
        )

        assert metadata.stock_count == 5100
        assert Path(metadata.output_file).exists()
        assert Path(metadata.output_file).with_suffix(
            ".json"
        ).exists()

    print("全市场数量校验成功")
    print("残缺行情拦截成功")
    print("CSV快照保存成功")
    print("JSON元数据保存成功")
