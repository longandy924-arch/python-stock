"""实时行情基础排序策略。

注意：
该模块仅用于验证实时流水线是否贯通，
不是正式 V45/V5 策略，不包含历史均线指标。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "ts_code",
    "name",
    "price",
    "pct_chg",
    "volume",
    "amount",
}


class RealtimeRankError(RuntimeError):
    """实时排序数据异常。"""


def _percentile_score(series: pd.Series) -> pd.Series:
    """将数值转换为0至100的分位评分。"""
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.rank(
        method="average",
        pct=True,
    ).fillna(0) * 100


def rank_realtime_quotes(
    quotes: pd.DataFrame,
    top_n: int = 20,
) -> pd.DataFrame:
    """对实时行情进行基础过滤和数据质量排序。"""

    if quotes is None or quotes.empty:
        raise RealtimeRankError("实时行情为空。")

    missing = REQUIRED_COLUMNS - set(quotes.columns)
    if missing:
        raise RealtimeRankError(
            f"缺少必要字段：{sorted(missing)}"
        )

    result = quotes.copy()

    numeric_columns = [
        "price",
        "pct_chg",
        "volume",
        "amount",
        "bid1",
        "ask1",
        "bid1_volume",
        "ask1_volume",
    ]

    for column in numeric_columns:
        if column in result.columns:
            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            )

    result["name"] = result["name"].astype(str).str.strip()
    result["ts_code"] = result["ts_code"].astype(str).str.strip()

    # 基础风险过滤，不代表正式策略条件
    result = result[
        result["price"].notna()
        & (result["price"] > 0)
        & result["amount"].notna()
        & (result["amount"] > 0)
        & ~result["name"].str.contains(
            r"ST|退市",
            case=False,
            regex=True,
            na=False,
        )
        & ~result["ts_code"].str.endswith(".BJ")
        & ~result["ts_code"].str.startswith("688")
    ].copy()

    if result.empty:
        raise RealtimeRankError("基础过滤后没有有效股票。")

    # 去除极端涨跌停附近股票，仅用于基础流水线测试
    result = result[
        result["pct_chg"].between(-9.5, 9.5)
    ].copy()

    if result.empty:
        raise RealtimeRankError("涨跌幅过滤后没有有效股票。")

    result["amount_score"] = _percentile_score(
        np.log1p(result["amount"])
    )

    result["volume_score"] = _percentile_score(
        np.log1p(result["volume"])
    )

    # 温和上涨优先；不是正式预测因子
    result["pct_quality"] = (
        100
        - (result["pct_chg"] - 2.0).abs() * 12
    ).clip(lower=0, upper=100)

    if {
        "bid1",
        "ask1",
        "bid1_volume",
        "ask1_volume",
    }.issubset(result.columns):
        total_order_volume = (
            result["bid1_volume"].fillna(0)
            + result["ask1_volume"].fillna(0)
        )

        result["order_balance"] = np.where(
            total_order_volume > 0,
            (
                result["bid1_volume"].fillna(0)
                - result["ask1_volume"].fillna(0)
            )
            / total_order_volume,
            0,
        )

        result["order_score"] = (
            (result["order_balance"] + 1) * 50
        ).clip(lower=0, upper=100)
    else:
        result["order_balance"] = 0.0
        result["order_score"] = 50.0

    result["realtime_score"] = (
        result["amount_score"] * 0.40
        + result["volume_score"] * 0.20
        + result["pct_quality"] * 0.25
        + result["order_score"] * 0.15
    ).round(2)

    output_columns = [
        "ts_code",
        "name",
        "price",
        "pct_chg",
        "volume",
        "amount",
        "bid1",
        "ask1",
        "bid1_volume",
        "ask1_volume",
        "order_balance",
        "realtime_score",
        "update_time",
    ]

    existing_columns = [
        column
        for column in output_columns
        if column in result.columns
    ]

    return (
        result[existing_columns]
        .sort_values(
            ["realtime_score", "amount"],
            ascending=[False, False],
        )
        .head(top_n)
        .reset_index(drop=True)
    )
