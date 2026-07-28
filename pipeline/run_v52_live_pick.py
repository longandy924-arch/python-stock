"""
V52 实盘唯一候选

正式口径：
1. 每日只推荐 1 支
2. 流通市值 < 500 亿
3. single_pick_score >= 0.70
4. 近4日涨幅 > 10%
5. 当日涨幅 > 3%
6. 买入后次日无论涨跌坚决卖出
"""

from __future__ import annotations

from pathlib import Path
import sys
from datetime import datetime

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from data_source.realtime_gateway import RealtimeGateway


DATA_DIR = BASE_DIR / "data" / "daily"
MV_FILE = BASE_DIR / "data" / "stock_basic_mv.csv"
OUTPUT_DIR = BASE_DIR / "output" / "live"
SCORE_THRESHOLD = 0.70
MAX_CIRC_MV = 5_000_000  # 单位：万元，等于500亿


def normalize_code(ts_code: str) -> str:
    return str(ts_code).strip()[:6].zfill(6)


def ma_trend_score(frame: pd.DataFrame) -> pd.Series:
    ma5 = frame["close"].rolling(5).mean()
    ma10 = frame["close"].rolling(10).mean()
    ma20 = frame["close"].rolling(20).mean()

    return (
        (frame["close"] > ma5).astype(int)
        + (ma5 > ma10).astype(int)
        + (ma10 > ma20).astype(int)
    ) / 3


def load_realtime() -> pd.DataFrame:
    gateway = RealtimeGateway()
    df = gateway.get_realtime_quotes()

    if df.empty:
        raise SystemExit("实时行情为空，停止选股。")

    required = ["ts_code", "name", "price", "pct_chg", "volume", "amount"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(f"实时行情缺少字段: {missing}")

    df = df.copy()
    df["code"] = df["ts_code"].map(normalize_code)

    for col in ["price", "pct_chg", "volume", "amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["price", "pct_chg", "amount"])
    df = df[df["price"] > 0].copy()

    print("实时行情源:", gateway.current_source)
    print("有效实时行情数量:", len(df))

    return df


def load_market_value() -> pd.DataFrame:
    if not MV_FILE.exists():
        raise SystemExit(f"未找到市值文件: {MV_FILE}")

    mv = pd.read_csv(MV_FILE, dtype={"ts_code": str})
    mv["code"] = mv["ts_code"].map(normalize_code)
    mv["circ_mv"] = pd.to_numeric(mv["circ_mv"], errors="coerce")

    return mv[["code", "circ_mv"]].drop_duplicates("code")


def build_live_candidates() -> pd.DataFrame:
    realtime = load_realtime()
    mv = load_market_value()

    realtime = realtime.merge(mv, on="code", how="left")
    realtime = realtime[realtime["circ_mv"].notna()].copy()

    rows = []
    today = datetime.now().strftime("%Y%m%d")

    files = list(DATA_DIR.glob("*.csv"))
    if len(files) < 3000:
        raise SystemExit(f"历史日线文件数量过少: {len(files)}")

    rt_map = realtime.set_index("code").to_dict("index")

    for index, path in enumerate(files, start=1):
        code = normalize_code(path.stem)
        rt = rt_map.get(code)
        if rt is None:
            continue

        try:
            hist = pd.read_csv(path, dtype={"date": str})
        except Exception:
            continue

        if len(hist) < 60:
            continue

        # 兼容字段
        if "ts_code" in hist.columns and "code" not in hist.columns:
            hist["code"] = hist["ts_code"].map(normalize_code)
        else:
            hist["code"] = code

        need_cols = ["date", "open", "close", "high", "low", "volume", "amount"]
        if any(c not in hist.columns for c in need_cols):
            continue

        hist = hist[need_cols + ["code"]].copy()

        for col in ["open", "close", "high", "low", "volume", "amount"]:
            hist[col] = pd.to_numeric(hist[col], errors="coerce")

        hist = hist.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)

        if hist.empty:
            continue

        live_price = float(rt["price"])
        live_row = {
            "date": today,
            "open": live_price,
            "close": live_price,
            "high": live_price,
            "low": live_price,
            "volume": float(rt["volume"]),
            "amount": float(rt["amount"]),
            "code": code,
        }

        frame = pd.concat([hist, pd.DataFrame([live_row])], ignore_index=True)
        frame = frame.sort_values("date").reset_index(drop=True)

        frame["pct"] = frame["close"] / frame["close"].shift(1) - 1
        frame["gain_4d"] = frame["close"] / frame["close"].shift(4) - 1
        frame["gain_5d"] = frame["close"] / frame["close"].shift(5) - 1
        frame["ma_trend_score"] = ma_trend_score(frame)

        last = frame.iloc[-1].copy()
        last["ts_code"] = rt["ts_code"]
        last["name"] = rt["name"]
        last["price"] = rt["price"]
        last["pct_chg"] = rt["pct_chg"]
        last["circ_mv"] = rt["circ_mv"]

        rows.append(last)

        if index % 500 == 0:
            print(f"V52实时因子计算: {index}/{len(files)}")

    if not rows:
        return pd.DataFrame()

    candidates = pd.DataFrame(rows)

    for col in ["pct", "gain_4d", "gain_5d", "amount", "ma_trend_score", "circ_mv"]:
        candidates[col] = pd.to_numeric(candidates[col], errors="coerce")

    # 实盘可买过滤：
    # 1. 流通市值 < 500亿
    # 2. 近4日涨幅 > 10%
    # 3. 当日涨幅 > 3%
    # 4. 剔除涨停或接近涨停，避免推荐买不进去的票
    # 5. 排除北交所 BJ、科创板 688
    candidates["pct_chg"] = pd.to_numeric(candidates["pct_chg"], errors="coerce")
    candidates["pct"] = candidates["pct_chg"] / 100
    candidates["ts_code"] = candidates["ts_code"].astype(str)

    # 东方财富实时行情没有直接提供换手率。
    # volume 单位近似为“手”，circ_mv 单位为“万元”。
    # turnover_pct 近似百分比 = volume * price / circ_mv
    candidates["turnover_pct"] = (
        pd.to_numeric(candidates["volume"], errors="coerce")
        * pd.to_numeric(candidates["price"], errors="coerce")
        / candidates["circ_mv"]
    )

    candidates = candidates[
        (candidates["circ_mv"] < MAX_CIRC_MV)
        & (candidates["gain_4d"] > 0.10)
        & (candidates["pct_chg"] > 3)
        & (candidates["pct_chg"] < 9.5)
        & ~candidates["ts_code"].str.endswith(".BJ")
        & ~candidates["ts_code"].str.startswith("688")
        & candidates["amount"].notna()
        & candidates["ma_trend_score"].notna()
    ].copy()

    if candidates.empty:
        return candidates

    candidates["rank_gain_4d"] = candidates["gain_4d"].rank(pct=True)
    candidates["rank_gain_5d"] = candidates["gain_5d"].rank(pct=True)
    candidates["rank_pct"] = candidates["pct"].rank(pct=True)
    candidates["rank_turnover"] = 1 - candidates["turnover_pct"].rank(pct=True)
    candidates["rank_amount"] = 1 - candidates["amount"].rank(pct=True)
    candidates["rank_ma_trend"] = candidates["ma_trend_score"].rank(pct=True)

    candidates["single_pick_score"] = candidates[
        [
            "rank_gain_4d",
            "rank_gain_5d",
            "rank_pct",
            "rank_turnover",
            "rank_amount",
            "rank_ma_trend",
        ]
    ].mean(axis=1)

    candidates = candidates[candidates["single_pick_score"] >= SCORE_THRESHOLD].copy()

    if candidates.empty:
        return candidates

    candidates = candidates.sort_values(
        ["single_pick_score", "circ_mv"],
        ascending=[False, True],
        kind="stable",
    )

    return candidates


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("V52 实盘唯一候选")
    print("=" * 60)

    candidates = build_live_candidates()

    if candidates.empty:
        print("今日无符合 V52 条件的候选，建议空仓。")
        return

    top = candidates.head(1).copy()

    out_file = OUTPUT_DIR / f"v52_live_pick_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    top.to_csv(out_file, index=False, encoding="utf-8-sig")

    row = top.iloc[0]

    print()
    print("今日唯一候选：")
    print(f"股票代码: {row['ts_code']}")
    print(f"股票名称: {row['name']}")
    print(f"当前价格: {row['price']}")
    print(f"当日涨幅: {row['pct_chg']}%")
    print(f"近4日涨幅: {round(row['gain_4d'] * 100, 2)}%")
    print(f"近5日涨幅: {round(row['gain_5d'] * 100, 2)}%")
    print(f"流通市值: {round(row['circ_mv'] / 10000, 2)} 亿")
    print(f"实时换手率估算: {round(row['turnover_pct'], 2)}%")
    print(f"V52评分: {round(row['single_pick_score'], 4)}")
    print(f"输出文件: {out_file}")
    print()
    print("执行规则: 今日只推荐这一支；次日无论涨跌坚决卖出。")


if __name__ == "__main__":
    main()
