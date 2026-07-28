"""Merge Engine核心逻辑测试。"""

from __future__ import annotations

import pandas as pd

from merge.merge_engine import merge_history_with_realtime
from strategy.indicators import calculate_indicators


def build_history(days: int = 120) -> pd.DataFrame:
    dates = pd.bdate_range(
        end="2026-07-27",
        periods=days,
    )

    rows = []

    for index, trade_date in enumerate(dates):
        close = 10 + index * 0.02

        rows.append(
            {
                "trade_date": trade_date,
                "open": close - 0.05,
                "high": close + 0.15,
                "low": close - 0.12,
                "close": close,
                "vol": 100000 + index * 100,
                "amount": 1000000 + index * 1000,
            }
        )

    return pd.DataFrame(rows)


def test_append_new_trade_day() -> None:
    history = build_history()

    realtime = {
        "price": 12.50,
        "open": 12.20,
        "high": 12.60,
        "low": 12.10,
        "volume": 250000,
        "amount": 3200000,
    }

    merged = merge_history_with_realtime(
        history,
        realtime,
        trade_date="2026-07-28",
        keep_days=120,
    )

    assert len(merged) == 120
    assert merged["trade_date"].is_unique
    assert merged.iloc[-1]["trade_date"] == pd.Timestamp(
        "2026-07-28"
    )
    assert merged.iloc[-1]["close"] == 12.50
    assert merged.iloc[-1]["data_source"] == "realtime_1430"


def test_replace_same_trade_day() -> None:
    history = build_history()

    today_row = history.iloc[-1].copy()
    today_row["trade_date"] = pd.Timestamp("2026-07-28")

    history = pd.concat(
        [history.iloc[:-1], pd.DataFrame([today_row])],
        ignore_index=True,
    )

    realtime = {
        "price": 13.00,
        "open": 12.60,
        "high": 13.10,
        "low": 12.50,
        "volume": 300000,
        "amount": 4000000,
    }

    merged = merge_history_with_realtime(
        history,
        realtime,
        trade_date="2026-07-28",
        keep_days=120,
    )

    assert len(merged) == 120
    assert merged["trade_date"].is_unique
    assert merged.iloc[-1]["close"] == 13.00
    assert merged.iloc[-1]["vol"] == 300000


def test_indicators_after_merge() -> None:
    history = build_history()

    realtime = {
        "price": 12.80,
        "open": 12.50,
        "high": 12.90,
        "low": 12.40,
        "volume": 280000,
        "amount": 3600000,
    }

    merged = merge_history_with_realtime(
        history,
        realtime,
        trade_date="2026-07-28",
        keep_days=120,
    )

    indicators = calculate_indicators(merged)

    latest = indicators.iloc[-1]

    assert pd.notna(latest["ma5"])
    assert pd.notna(latest["ma10"])
    assert pd.notna(latest["ma20"])
    assert pd.notna(latest["vol_ratio"])
    assert pd.notna(latest["close_strength"])


if __name__ == "__main__":
    test_append_new_trade_day()
    test_replace_same_trade_day()
    test_indicators_after_merge()

    print("新交易日追加验证通过")
    print("同交易日替换验证通过")
    print("重复日期检查通过")
    print("MA5/MA10/MA20计算通过")
    print("Merge Engine核心逻辑验证成功")
