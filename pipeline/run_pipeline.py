"""14:55实时数据流水线 V1。

当前只验证：
1. 实时行情获取；
2. 全市场数据完整性；
3. 快照保存；
4. 基础过滤和实时排序；
5. 候选结果保存。

本版本不计算历史均线，也不是正式V45策略。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from data_source.realtime_gateway import RealtimeGateway
from realtime.collect_1455 import (
    save_snapshot,
    validate_snapshot,
)
from strategy.realtime_rank_strategy import (
    rank_realtime_quotes,
)


def run_pipeline(
    top_n: int = 20,
    minimum_stock_count: int = 5000,
    output_root: Path | str = "output",
) -> Path:
    """运行一次实时行情流水线。"""

    output_root = Path(output_root)
    gateway = RealtimeGateway()

    print("步骤1/4：获取全市场实时行情")
    quotes = gateway.get_realtime_quotes()

    print("步骤2/4：校验并保存实时快照")
    validated = validate_snapshot(
        quotes,
        minimum_stock_count=minimum_stock_count,
    )

    snapshot_metadata = save_snapshot(
        validated,
        gateway=gateway,
        output_root=output_root / "realtime",
    )

    print("步骤3/4：执行基础过滤与实时排序")
    ranked = rank_realtime_quotes(
        validated,
        top_n=top_n,
    )

    if ranked.empty:
        raise RuntimeError("实时排序结果为空。")

    print("步骤4/4：保存候选结果")
    now = datetime.now()
    result_dir = output_root / "results" / now.strftime("%Y%m%d")
    result_dir.mkdir(parents=True, exist_ok=True)

    result_path = result_dir / (
        f"realtime_rank_{now.strftime('%H%M%S')}.csv"
    )
    metadata_path = result_path.with_suffix(".json")

    ranked.to_csv(
        result_path,
        index=False,
        encoding="utf-8-sig",
    )

    pipeline_metadata = {
        "run_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "pipeline_version": "V1",
        "result_type": "realtime_data_quality_rank",
        "formal_strategy": False,
        "provider": gateway.current_source,
        "provider_switched": gateway.switched,
        "response_time_ms": gateway.response_time_ms,
        "market_stock_count": len(validated),
        "candidate_count": len(ranked),
        "snapshot": asdict(snapshot_metadata),
        "result_file": str(result_path),
    }

    metadata_path.write_text(
        json.dumps(
            pipeline_metadata,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 62)
    print("实时行情流水线 V1 运行成功")
    print("=" * 62)
    print(f"数据源：{gateway.current_source}")
    print(f"是否切换数据源：{gateway.switched}")
    print(f"全市场股票数量：{len(validated)}")
    print(f"输出候选数量：{len(ranked)}")
    print(f"结果文件：{result_path}")
    print("\n前10名：")
    print(ranked.head(10).to_string(index=False))
    print("\n注意：当前结果仅用于验证流水线，不是正式买入信号。")

    return result_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="运行14:55实时行情流水线"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--minimum-stock-count",
        type=int,
        default=5000,
    )
    parser.add_argument(
        "--output-root",
        default="output",
    )
    args = parser.parse_args()

    try:
        run_pipeline(
            top_n=args.top_n,
            minimum_stock_count=args.minimum_stock_count,
            output_root=args.output_root,
        )
    except Exception as exc:
        print(f"流水线运行失败：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
