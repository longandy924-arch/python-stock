"""历史日线与14:30实时行情合并引擎。"""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd


HISTORY_REQUIRED_COLUMNS = {
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "vol",
}

REALTIME_REQUIRED_COLUMNS = {
    "price",
    "volume",
}


class MergeDataError(RuntimeError):
    """历史数据或实时数据不符合合并要求。"""


def _normalise_trade_date(value: object) -> pd.Timestamp:
    """将日期统一转换为无时分秒的Timestamp。"""
    timestamp = pd.to_datetime(value, errors="coerce")

    if pd.isna(timestamp):
        raise MergeDataError(f"无法识别交易日期：{value}")

    return timestamp.normalize()


def _prepare_history(history: pd.DataFrame) -> pd.DataFrame:
    """清洗历史日线。"""
    if history is None or history.empty:
        raise MergeDataError("历史日线为空。")

    missing = HISTORY_REQUIRED_COLUMNS - set(history.columns)
    if missing:
        raise MergeDataError(
            f"历史日线缺少字段：{sorted(missing)}"
        )

    result = history.copy()

    result["trade_date"] = pd.to_datetime(
        result["trade_date"],
        errors="coerce",
    ).dt.normalize()

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "vol",
        "amount",
        "pre_close",
        "pct_chg",
    ]

    for column in numeric_columns:
        if column in result.columns:
            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            )

    result = result.dropna(
        subset=[
            "trade_date",
            "open",
            "high",
            "low",
            "close",
            "vol",
        ]
    )

    result = (
        result.sort_values("trade_date")
        .drop_duplicates(
            subset=["trade_date"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    if result.empty:
        raise MergeDataError("历史日线清洗后为空。")

    invalid_price = (
        (result["open"] <= 0)
        | (result["high"] <= 0)
        | (result["low"] <= 0)
        | (result["close"] <= 0)
    )

    if invalid_price.any():
        raise MergeDataError("历史日线存在无效价格。")

    return result


def _extract_realtime_value(
    realtime: pd.Series,
    names: tuple[str, ...],
    default: float | None = None,
) -> float:
    """从多个候选字段中提取第一个有效数值。"""
    for name in names:
        if name not in realtime.index:
            continue

        value = pd.to_numeric(
            pd.Series([realtime[name]]),
            errors="coerce",
        ).iloc[0]

        if pd.notna(value):
            return float(value)

    if default is not None:
        return float(default)

    raise MergeDataError(
        f"实时行情缺少有效字段：{list(names)}"
    )


def merge_history_with_realtime(
    history: pd.DataFrame,
    realtime: pd.Series | dict,
    trade_date: str | date | datetime | pd.Timestamp,
    keep_days: int = 120,
) -> pd.DataFrame:
    """
    合并单只股票历史日线与当天14:30实时行情。

    同一交易日：
        使用实时数据替换当天最后一行。

    新交易日：
        在历史日线末尾追加当天实时K线。
    """

    if keep_days < 21:
        raise MergeDataError("至少保留21个交易日。")

    result = _prepare_history(history)

    if isinstance(realtime, dict):
        realtime_row = pd.Series(realtime)
    elif isinstance(realtime, pd.Series):
        realtime_row = realtime.copy()
    else:
        raise MergeDataError("实时行情必须是Series或dict。")

    missing = REALTIME_REQUIRED_COLUMNS - set(realtime_row.index)
    if missing:
        raise MergeDataError(
            f"实时行情缺少字段：{sorted(missing)}"
        )

    current_date = _normalise_trade_date(trade_date)
    last_history_date = result["trade_date"].max()

    if current_date < last_history_date:
        raise MergeDataError(
            "实时交易日期早于历史数据最后日期。"
        )

    price = _extract_realtime_value(
        realtime_row,
        ("price", "close"),
    )

    if price <= 0:
        raise MergeDataError("实时价格无效。")

    previous_close = float(result.iloc[-1]["close"])

    open_price = _extract_realtime_value(
        realtime_row,
        ("open",),
        default=price,
    )

    high_price = _extract_realtime_value(
        realtime_row,
        ("high",),
        default=max(open_price, price),
    )

    low_price = _extract_realtime_value(
        realtime_row,
        ("low",),
        default=min(open_price, price),
    )

    volume = _extract_realtime_value(
        realtime_row,
        ("volume", "vol"),
        default=0,
    )

    amount = _extract_realtime_value(
        realtime_row,
        ("amount",),
        default=0,
    )

    high_price = max(high_price, open_price, price)
    low_price = min(low_price, open_price, price)

    realtime_daily = {
        "trade_date": current_date,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": price,
        "vol": volume,
        "amount": amount,
        "pre_close": previous_close,
        "pct_chg": (
            (price / previous_close - 1) * 100
            if previous_close > 0
            else 0
        ),
        "data_source": "realtime_1430",
        "is_realtime": True,
    }

    if current_date == last_history_date:
        previous_close_same_day = (
            float(result.iloc[-2]["close"])
            if len(result) >= 2
            else previous_close
        )

        realtime_daily["pre_close"] = previous_close_same_day
        realtime_daily["pct_chg"] = (
            (
                price / previous_close_same_day - 1
            )
            * 100
            if previous_close_same_day > 0
            else 0
        )

        result = result[
            result["trade_date"] != current_date
        ].copy()

    realtime_frame = pd.DataFrame([realtime_daily])

    for column in result.columns:
        if column not in realtime_frame.columns:
            realtime_frame[column] = pd.NA

    for column in realtime_frame.columns:
        if column not in result.columns:
            result[column] = pd.NA

    realtime_frame = realtime_frame[result.columns]

    merged = pd.concat(
        [result, realtime_frame],
        ignore_index=True,
    )

    merged = (
        merged.sort_values("trade_date")
        .drop_duplicates(
            subset=["trade_date"],
            keep="last",
        )
        .tail(keep_days)
        .reset_index(drop=True)
    )

    if merged["trade_date"].duplicated().any():
        raise MergeDataError("合并后存在重复交易日期。")

    if merged.iloc[-1]["trade_date"] != current_date:
        raise MergeDataError("实时行情未正确写入最后一行。")

    required_prices = merged[
        ["open", "high", "low", "close"]
    ].apply(
        pd.to_numeric,
        errors="coerce",
    )

    if required_prices.isna().any().any():
        raise MergeDataError("合并后存在空价格。")

    if (required_prices <= 0).any().any():
        raise MergeDataError("合并后存在无效价格。")

    return merged
