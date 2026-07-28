"""实时行情排序与流水线核心逻辑测试。"""

import pandas as pd

from realtime.collect_1455 import validate_snapshot
from strategy.realtime_rank_strategy import (
    rank_realtime_quotes,
)


def build_quotes(count: int = 5100) -> pd.DataFrame:
    rows = []

    for index in range(count):
        symbol = f"{index:06d}.SZ"

        rows.append(
            {
                "ts_code": symbol,
                "name": f"测试股票{index}",
                "price": 10 + index % 20,
                "pct_chg": (index % 80) / 10 - 3,
                "volume": 100000 + index * 10,
                "amount": 1000000 + index * 100,
                "bid1": 10.00,
                "ask1": 10.01,
                "bid1_volume": 1200 + index,
                "ask1_volume": 1000 + index,
                "update_time": "2026-07-28 14:55:00",
            }
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    source = build_quotes()

    validated = validate_snapshot(
        source,
        minimum_stock_count=5000,
    )

    ranked = rank_realtime_quotes(
        validated,
        top_n=20,
    )

    assert len(validated) == 5100
    assert len(ranked) == 20
    assert ranked["realtime_score"].notna().all()
    assert ranked["realtime_score"].is_monotonic_decreasing
    assert ranked["ts_code"].is_unique

    print("全市场快照校验通过")
    print("实时排序逻辑验证通过")
    print("候选数量限制验证通过")
    print("评分降序验证通过")
