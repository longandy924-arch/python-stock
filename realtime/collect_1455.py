"""14:55 全市场实时行情快照采集器 V1。"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from data_source.realtime_gateway import RealtimeGateway


REQUIRED_COLUMNS = {
    "ts_code",
    "name",
    "price",
    "pct_chg",
    "volume",
    "amount",
    "update_time",
}


class SnapshotValidationError(RuntimeError):
    """实时快照验证失败。"""


@dataclass
class SnapshotMetadata:
    collected_at: str
    provider: str
    response_time_ms: float
    stock_count: int
    valid_price_count: int
    output_file: str
    status: str


def validate_snapshot(
    quotes: pd.DataFrame,
    minimum_stock_count: int = 5000,
) -> pd.DataFrame:
    """验证全市场快照，防止把残缺数据当作成功结果。"""

    if quotes is None or quotes.empty:
        raise SnapshotValidationError("实时行情为空。")

    missing = REQUIRED_COLUMNS - set(quotes.columns)
    if missing:
        raise SnapshotValidationError(
            f"缺少必要字段：{sorted(missing)}"
        )

    result = quotes.copy()
    result["price"] = pd.to_numeric(
        result["price"],
        errors="coerce",
    )

    result = result.drop_duplicates(
        subset=["ts_code"],
        keep="first",
    )

    if len(result) < minimum_stock_count:
        raise SnapshotValidationError(
            f"股票数量不足：仅{len(result)}只，"
            f"全市场采集要求至少{minimum_stock_count}只。"
        )

    valid_price_count = int(
        result["price"].notna().sum()
    )
    valid_price_rate = valid_price_count / len(result)

    if valid_price_rate < 0.90:
        raise SnapshotValidationError(
            f"有效价格比例过低：{valid_price_rate:.2%}"
        )

    result["collected_at"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    return result.sort_values(
        "ts_code"
    ).reset_index(drop=True)


def save_snapshot(
    quotes: pd.DataFrame,
    gateway: RealtimeGateway,
    output_root: Path | str = "output/realtime",
) -> SnapshotMetadata:
    """保存快照和采集元数据。"""

    now = datetime.now()
    output_dir = Path(output_root) / now.strftime("%Y%m%d")
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = f"quotes_{now.strftime('%H%M%S')}"
    csv_path = output_dir / f"{stem}.csv"
    metadata_path = output_dir / f"{stem}.json"

    quotes.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
    )

    metadata = SnapshotMetadata(
        collected_at=now.strftime("%Y-%m-%d %H:%M:%S"),
        provider=gateway.current_source or "unknown",
        response_time_ms=gateway.response_time_ms,
        stock_count=len(quotes),
        valid_price_count=int(
            quotes["price"].notna().sum()
        ),
        output_file=str(csv_path),
        status="success",
    )

    metadata_path.write_text(
        json.dumps(
            asdict(metadata),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return metadata


def collect_snapshot(
    minimum_stock_count: int = 5000,
    output_root: Path | str = "output/realtime",
) -> SnapshotMetadata:
    """获取、验证并保存一次全市场实时快照。"""

    gateway = RealtimeGateway()

    started = time.perf_counter()
    quotes = gateway.get_realtime_quotes()
    total_elapsed_ms = round(
        (time.perf_counter() - started) * 1000,
        2,
    )

    validated = validate_snapshot(
        quotes,
        minimum_stock_count=minimum_stock_count,
    )

    metadata = save_snapshot(
        validated,
        gateway=gateway,
        output_root=output_root,
    )

    print("=" * 60)
    print("14:55实时行情快照采集成功")
    print("=" * 60)
    print(f"数据源：{metadata.provider}")
    print(f"股票数量：{metadata.stock_count}")
    print(f"有效价格：{metadata.valid_price_count}")
    print(f"Gateway响应：{metadata.response_time_ms}ms")
    print(f"采集总耗时：{total_elapsed_ms}ms")
    print(f"保存文件：{metadata.output_file}")

    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(
        description="采集全市场实时行情快照"
    )
    parser.add_argument(
        "--minimum-stock-count",
        type=int,
        default=5000,
    )
    parser.add_argument(
        "--output-root",
        default="output/realtime",
    )
    args = parser.parse_args()

    try:
        collect_snapshot(
            minimum_stock_count=args.minimum_stock_count,
            output_root=args.output_root,
        )
    except Exception as exc:
        print(f"实时快照采集失败：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
