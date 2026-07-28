"""
检查 GitHub 仓库内实时行情是否可供 V52 使用。

目标：
1. 调用 RealtimeGateway 获取全市场实时行情
2. 验证 V52 实盘所需字段是否存在
3. 输出实时数据规模和样例
"""

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from data_source.realtime_gateway import RealtimeGateway


REQUIRED_COLUMNS = [
    "ts_code",
    "name",
    "price",
    "pct_chg",
    "volume",
    "amount",
]


def main() -> None:
    gateway = RealtimeGateway()
    df = gateway.get_realtime_quotes()

    print("=" * 60)
    print("V52 实时行情检查")
    print("=" * 60)

    print("数据源:", gateway.current_source)
    print("实时行情数量:", len(df))

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]

    if missing:
        print("缺失字段:", missing)
        raise SystemExit("实时行情字段不完整，不能进入 V52 实盘计算。")

    if len(df) < 5000:
        raise SystemExit(f"实时行情数量过少: {len(df)}，不能作为全市场选股依据。")

    print("字段检查: 通过")
    print()
    print("前10行实时行情:")
    print(df[REQUIRED_COLUMNS].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
