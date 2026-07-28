"""V5 基础指标计算模块。"""

from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {"open", "high", "low", "close", "vol"}


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算V5基础指标，不使用未来数据。"""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"缺少必要字段：{sorted(missing)}")

    result = df.copy()

    for column in REQUIRED_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    result["pct"] = result["close"].pct_change() * 100

    result["amplitude"] = np.where(
        result["open"] != 0,
        (result["high"] - result["low"]) / result["open"] * 100,
        np.nan,
    )

    price_range = result["high"] - result["low"]
    result["close_strength"] = np.where(
        price_range != 0,
        (result["close"] - result["low"]) / price_range,
        0.5,
    )

    result["ma5"] = result["close"].rolling(5).mean()
    result["ma10"] = result["close"].rolling(10).mean()
    result["ma20"] = result["close"].rolling(20).mean()

    result["vol_ma5"] = result["vol"].rolling(5).mean()
    result["vol_ratio"] = np.where(
        result["vol_ma5"] != 0,
        result["vol"] / result["vol_ma5"],
        np.nan,
    )

    result["trend_ma5"] = result["close"] > result["ma5"]
    result["trend_ma10"] = result["close"] > result["ma10"]
    result["trend_ma20"] = result["close"] > result["ma20"]

    return result


def validate_no_future_data(df: pd.DataFrame) -> bool:
    """
    验证最后一行数据变化不会影响此前指标。
    用于检查是否误用了未来数据。
    """
    if len(df) < 21:
        raise ValueError("至少需要21行数据进行未来函数验证。")

    original = calculate_indicators(df)
    modified = df.copy()
    modified.loc[modified.index[-1], "close"] *= 10
    changed = calculate_indicators(modified)

    columns = [
        "pct",
        "amplitude",
        "close_strength",
        "ma5",
        "ma10",
        "ma20",
        "vol_ratio",
    ]

    return original.iloc[:-1][columns].equals(changed.iloc[:-1][columns])
