"""
V52 每日选股入口

规则：
1. 每日只推荐 1 支股票
2. 流通市值 < 500 亿
3. single_pick_score >= 0.70
4. 买入后次日无论涨跌坚决卖出
"""

from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RESULT_FILE = BASE_DIR / "output" / "results" / "V52_top1_score70_result.csv"


def load_latest_pick() -> pd.DataFrame:
    if not RESULT_FILE.exists():
        raise FileNotFoundError(f"未找到结果文件: {RESULT_FILE}")

    df = pd.read_csv(RESULT_FILE)

    if df.empty:
        return df

    df["交易日期"] = pd.to_datetime(df["交易日期"])
    latest_date = df["交易日期"].max()

    latest = (
        df[df["交易日期"] == latest_date]
        .sort_values("single_pick_score", ascending=False)
        .head(1)
        .copy()
    )

    return latest


def main() -> None:
    latest = load_latest_pick()

    print("=" * 60)
    print("V52 每日唯一候选")
    print("=" * 60)

    if latest.empty:
        print("今日无符合 V52 条件的候选，建议空仓。")
        return

    row = latest.iloc[0]

    print(f"交易日期: {row['交易日期'].date()}")
    print(f"股票代码: {row['股票代码']}")
    print(f"股票名称: {row['股票名称']}")
    print(f"买入价格: {row['买入价格']}")
    print(f"策略评分: {row['single_pick_score']}")
    print(f"历史验证收益率: {row['收益率']}%")
    print()
    print("执行规则: 今日只推荐这一支；次日无论涨跌坚决卖出。")


if __name__ == "__main__":
    main()
