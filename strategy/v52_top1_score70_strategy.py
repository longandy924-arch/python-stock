#!/usr/bin/env python3
"""Build a single-pick daily model from the V48 B leading-strength setup."""

from __future__ import annotations

import bisect
import os
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = (BASE_DIR / "../../data").resolve()
STOCK_BASIC_FILE = BASE_DIR / "stock_basic.csv"
RESULT_FILE = BASE_DIR / "V52_top1_score70_result.csv"

START_DATE = "2024-01-02"
TARGET_RETURN = 0.025
TURNOVER_THRESHOLD = 2.0
AMOUNT_THRESHOLD_YUAN = 200_000_000

RESULT_COLUMNS = [
    "交易日期",
    "股票代码",
    "股票名称",
    "买入价格",
    "次日最高价",
    "收益率",
    "成功失败",
    "single_pick_score",
    "gain_4d",
    "gain_5d",
    "pct",
    "turnover_pct",
    "amount",
    "ma_trend_score",
]


def normalize_code(value: object) -> str:
    return str(value).split(".", 1)[0].zfill(6)


def normalize_turnover(value: float) -> float:
    return value * 100 if pd.notna(value) and abs(value) <= 1 else value


def expanding_rank_pct(values: pd.Series) -> pd.Series:
    seen: list[float] = []
    ranks: list[float | None] = []
    for value in values:
        if pd.isna(value):
            ranks.append(None)
            continue
        number = float(value)
        bisect.insort(seen, number)
        left = bisect.bisect_left(seen, number)
        right = bisect.bisect_right(seen, number)
        ranks.append(((left + 1 + right) / 2) / len(seen))
    return pd.Series(ranks, index=values.index, dtype="float64")


def max_consecutive_failures(success: pd.Series) -> int:
    max_run = 0
    current = 0
    for value in success.astype(bool):
        if value:
            current = 0
        else:
            current += 1
            max_run = max(max_run, current)
    return max_run


def load_metadata() -> pd.DataFrame:
    basic = pd.read_csv(STOCK_BASIC_FILE, dtype={"ts_code": str})
    basic["code"] = basic["ts_code"].map(normalize_code)
    return basic[["code", "name", "market"]].drop_duplicates("code")


def limit_threshold(name: object, market: object) -> float:
    name_text = str(name)
    market_text = str(market)
    if "ST" in name_text.upper():
        return 0.0475
    if "北交" in market_text:
        return 0.295
    if market_text in {"创业板", "科创板"}:
        return 0.195
    return 0.095


def add_limit_flags(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["limit_threshold"] = [
        limit_threshold(name, market)
        for name, market in zip(result["name"], result["market"])
    ]
    tolerance = 0.001
    result["limit_up"] = result["pct"] >= result["limit_threshold"]
    result["rise_ge_95"] = result["pct"] >= 0.095
    result["one_word_limit"] = (
        result["limit_up"]
        & np.isclose(result["open"], result["high"], atol=tolerance, rtol=0)
        & np.isclose(result["open"], result["low"], atol=tolerance, rtol=0)
        & np.isclose(result["open"], result["close"], atol=tolerance, rtol=0)
    )
    result["sealed_limit"] = (
        result["limit_up"]
        & np.isclose(result["close"], result["high"], atol=tolerance, rtol=0)
    )
    result["untradable"] = (
        result["rise_ge_95"]
        | result["limit_up"]
        | result["one_word_limit"]
        | result["sealed_limit"]
    )
    return result


def ma_trend_score(frame: pd.DataFrame) -> pd.Series:
    ma5 = frame["close"].rolling(5).mean()
    ma10 = frame["close"].rolling(10).mean()
    ma20 = frame["close"].rolling(20).mean()
    return (
        (frame["close"] > ma5).astype(int)
        + (ma5 > ma10).astype(int)
        + (ma10 > ma20).astype(int)
    ) / 3


def load_candidates() -> pd.DataFrame:
    metadata = load_metadata()
    frames: list[pd.DataFrame] = []
    files = [name for name in os.listdir(DATA_DIR) if name.endswith(".csv")]
    for index, filename in enumerate(files):
        path = DATA_DIR / filename
        try:
            frame = pd.read_csv(
                path,
                usecols=[
                    "date",
                    "open",
                    "close",
                    "high",
                    "low",
                    "volume",
                    "amount",
                    "turnover",
                ],
                dtype={"date": str},
            )
        except (OSError, ValueError, KeyError, pd.errors.ParserError):
            continue
        if len(frame) < 60:
            continue

        frame = frame.sort_values("date").reset_index(drop=True)
        for column in ["open", "close", "high", "low", "volume", "amount", "turnover"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

        frame["code"] = normalize_code(filename.removesuffix(".csv"))
        frame["pct"] = frame["close"] / frame["close"].shift(1) - 1
        frame["gain_4d"] = frame["close"] / frame["close"].shift(4) - 1
        frame["gain_5d"] = frame["close"] / frame["close"].shift(5) - 1
        frame["market_cap_proxy"] = frame["close"] * frame["volume"]
        frame["momentum5"] = frame["close"] / frame["close"].shift(5) - 1
        frame["trend"] = (frame["close"] > frame["close"].rolling(5).mean()).astype(int)
        frame["volatility"] = (
            frame["high"].rolling(5).max() - frame["low"].rolling(5).min()
        ) / frame["close"]
        frame["ma_trend_score"] = ma_trend_score(frame)

        frame["market_cap_rank"] = expanding_rank_pct(frame["market_cap_proxy"])
        frame["momentum5_rank"] = expanding_rank_pct(frame["momentum5"])
        frame["amount_rank"] = expanding_rank_pct(frame["amount"])
        frame["trend_rank"] = expanding_rank_pct(frame["trend"])
        frame["volatility_rank"] = expanding_rank_pct(frame["volatility"])
        frame["v40_score"] = (
            frame["market_cap_rank"] * -0.25
            + frame["momentum5_rank"] * 0.25
            + frame["amount_rank"] * 0.20
            + frame["trend_rank"] * 0.20
            + frame["volatility_rank"] * 0.10
        )

        frame["buy_price"] = frame["close"]
        frame["next_day_high"] = frame["high"].shift(-1)
        frame["high_return"] = frame["next_day_high"] / frame["buy_price"] - 1
        frame["turnover_pct"] = frame["turnover"].map(normalize_turnover)
        frame = frame[frame["date"] >= START_DATE].copy()
        frames.append(
            frame[
                [
                    "date",
                    "code",
                    "open",
                    "close",
                    "high",
                    "low",
                    "pct",
                    "gain_4d",
                    "gain_5d",
                    "v40_score",
                    "amount",
                    "turnover_pct",
                    "ma_trend_score",
                    "buy_price",
                    "next_day_high",
                    "high_return",
                ]
            ]
        )
        if index and index % 500 == 0:
            print(f"V49每日唯一推荐读取: {index}/{len(files)}")

    if not frames:
        raise RuntimeError("没有可用日线数据")
    candidates = pd.concat(frames, ignore_index=True)
    candidates = candidates.merge(metadata, on="code", how="left")

    mv = pd.read_csv(
        BASE_DIR / "stock_basic_mv.csv",
        dtype={"ts_code": str},
    )

    mv["code"] = mv["ts_code"].astype(str).str[:6]

    candidates = candidates.merge(
        mv[["code", "circ_mv"]],
        on="code",
        how="left",
    )

    return add_limit_flags(candidates)


def add_single_pick_score(pool: pd.DataFrame) -> pd.DataFrame:
    result = pool.copy()
    grouped = result.groupby("date", group_keys=False)
    result["rank_gain_4d"] = grouped["gain_4d"].rank(pct=True)
    result["rank_gain_5d"] = grouped["gain_5d"].rank(pct=True)
    result["rank_pct"] = grouped["pct"].rank(pct=True)
    result["rank_turnover"] = 1 - grouped["turnover_pct"].rank(pct=True)
    result["rank_amount"] = 1 - grouped["amount"].rank(pct=True)
    result["rank_ma_trend"] = grouped["ma_trend_score"].rank(pct=True)
    result["single_pick_score"] = result[
        [
            "rank_gain_4d",
            "rank_gain_5d",
            "rank_pct",
            "rank_turnover",
            "rank_amount",
            "rank_ma_trend",
        ]
    ].mean(axis=1)
    return result


def select_daily_top1(candidates: pd.DataFrame) -> pd.DataFrame:
    mask = (
        (candidates["turnover_pct"] <= TURNOVER_THRESHOLD)
        & (candidates["amount"] <= AMOUNT_THRESHOLD_YUAN)
        & (candidates["gain_4d"] > 0.10)
        & (candidates["pct"] > 0.03)
        & candidates["circ_mv"].notna()
        & (candidates["circ_mv"] < 5_000_000)
        & ~candidates["untradable"]
    )
    pool = add_single_pick_score(candidates[mask.fillna(False)].copy())
    pool = pool[pool["single_pick_score"] >= 0.70].copy()

    selected = (
        pool.sort_values(
            ["date", "single_pick_score", "v40_score"],
            ascending=[True, False, False],
            kind="stable",
        )
        .groupby("date", sort=False)
        .head(1)
        .dropna(subset=["high_return"])
        .copy()
        .reset_index(drop=True)
    )
    selected["success"] = selected["high_return"] >= TARGET_RETURN
    return selected


def build_output(trades: pd.DataFrame) -> pd.DataFrame:
    output = pd.DataFrame(
        {
            "交易日期": trades["date"],
            "股票代码": trades["code"],
            "股票名称": trades["name"],
            "买入价格": trades["buy_price"].round(3),
            "次日最高价": trades["next_day_high"].round(3),
            "收益率": (trades["high_return"] * 100).round(2),
            "成功失败": np.where(trades["success"], "成功", "失败"),
            "single_pick_score": trades["single_pick_score"].round(4),
            "gain_4d": (trades["gain_4d"] * 100).round(2),
            "gain_5d": (trades["gain_5d"] * 100).round(2),
            "pct": (trades["pct"] * 100).round(2),
            "turnover_pct": trades["turnover_pct"].round(2),
            "amount": trades["amount"].round(2),
            "ma_trend_score": trades["ma_trend_score"].round(4),
        }
    )
    return output[RESULT_COLUMNS]


def main() -> None:
    candidates = load_candidates()
    trades = select_daily_top1(candidates)
    result = build_output(trades)
    result.to_csv(RESULT_FILE, index=False)

    sample = len(trades)
    success = int(trades["success"].sum()) if sample else 0
    failure = sample - success
    win_rate = success / sample * 100 if sample else 0.0
    avg_return = trades["high_return"].mean() * 100 if sample else 0.0
    max_failures = max_consecutive_failures(trades["success"]) if sample else 0

    print(f"总交易次数：{sample}")
    print(f"成功次数：{success}")
    print(f"失败次数：{failure}")
    print(f"胜率：{win_rate:.2f}%")
    print(f"平均收益：{avg_return:.2f}%")
    print(f"最大连续失败：{max_failures}")


if __name__ == "__main__":
    main()
