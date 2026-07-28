"""
V52 实盘输入检查

检查内容：
1. 实时行情是否可用
2. 市值文件是否可用
3. 历史日线文件是否可用
4. 三类数据能否按股票代码合并
"""

from pathlib import Path
import sys
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from data_source.realtime_gateway import RealtimeGateway


def main() -> None:
    print("=" * 60)
    print("V52 实盘输入检查")
    print("=" * 60)

    # 1. 实时行情
    gateway = RealtimeGateway()
    realtime = gateway.get_realtime_quotes()
    print("实时行情源:", gateway.current_source)
    print("实时行情数量:", len(realtime))

    if "ts_code" not in realtime.columns:
        raise SystemExit("实时行情缺少 ts_code 字段")

    realtime["code"] = realtime["ts_code"].astype(str).str[:6]

    # 2. 市值文件
    mv_path = BASE_DIR / "data" / "stock_basic_mv.csv"

    print("市值文件:", mv_path)

    if not mv_path.exists():
        raise SystemExit("未找到 stock_basic_mv.csv，无法做500亿市值过滤")

    mv = pd.read_csv(mv_path, dtype={"ts_code": str})
    mv["code"] = mv["ts_code"].astype(str).str[:6]
    mv["circ_mv"] = pd.to_numeric(mv["circ_mv"], errors="coerce")

    print("市值数据数量:", len(mv))

    # 3. 历史日线目录
    data_dirs = [
        BASE_DIR / "data" / "daily",
        BASE_DIR / "data",
        BASE_DIR / "backtest" / "v9" / "data",
    ]

    data_dir = None
    for d in data_dirs:
        if d.exists() and list(d.glob("*.csv")):
            data_dir = d
            break

    print("历史日线目录:", data_dir)

    if data_dir is None:
        raise SystemExit("未找到历史日线CSV目录，无法计算V52因子")

    files = [
        f for f in data_dir.glob("*.csv")
        if f.name != "stock_basic_mv.csv"
    ]
    print("历史日线文件数量:", len(files))

    if len(files) < 3000:
        raise SystemExit(
            f"历史日线文件数量过少: {len(files)}，疑似没有迁移全市场日线数据，不能进入V52实盘选股"
        )

    # 4. 合并检查
    merged = realtime.merge(
        mv[["code", "circ_mv"]],
        on="code",
        how="left",
    )

    print("实时+市值匹配数量:", int(merged["circ_mv"].notna().sum()))

    if merged["circ_mv"].notna().sum() < 4000:
        raise SystemExit("实时行情与市值数据匹配过少，不能进入实盘选股")

    print()
    print("样例：")
    cols = [c for c in ["ts_code", "name", "price", "pct_chg", "amount", "circ_mv"] if c in merged.columns]
    print(merged[cols].head(10).to_string(index=False))

    print()
    print("V52实盘输入检查：通过")


if __name__ == "__main__":
    main()
