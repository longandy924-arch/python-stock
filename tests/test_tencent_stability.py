"""腾讯实时行情连续稳定性测试。"""

from __future__ import annotations

import csv
import statistics
import time
from datetime import datetime
from pathlib import Path

from data_source.providers.tencent_provider import (
    TencentRealtimeProvider,
)


TOTAL_RUNS = 100
REQUEST_INTERVAL_SECONDS = 0.2
OUTPUT_PATH = Path("output/tencent_stability.csv")


def main() -> None:
    provider = TencentRealtimeProvider(
        ts_codes=[
            "000001.SZ",
            "600000.SH",
            "300750.SZ",
        ],
        timeout=10.0,
    )

    records: list[dict[str, object]] = []
    response_times: list[float] = []
    success_count = 0
    failure_count = 0

    print(f"开始腾讯实时行情稳定性测试：{TOTAL_RUNS}次")

    for run_no in range(1, TOTAL_RUNS + 1):
        started = time.perf_counter()
        success = False
        stock_count = 0
        error = ""

        try:
            quotes = provider.get_quotes()
            elapsed_ms = round(
                (time.perf_counter() - started) * 1000,
                2,
            )

            if quotes.empty:
                raise RuntimeError("返回数据为空")

            success = True
            stock_count = len(quotes)
            success_count += 1
            response_times.append(elapsed_ms)

        except Exception as exc:
            elapsed_ms = round(
                (time.perf_counter() - started) * 1000,
                2,
            )
            failure_count += 1
            error = str(exc)

        records.append(
            {
                "run_no": run_no,
                "time": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "success": success,
                "response_ms": elapsed_ms,
                "stock_count": stock_count,
                "error": error,
            }
        )

        status = "成功" if success else "失败"
        print(
            f"{run_no:03d}/{TOTAL_RUNS} "
            f"{status} 响应={elapsed_ms}ms "
            f"数量={stock_count}"
        )

        if run_no < TOTAL_RUNS:
            time.sleep(REQUEST_INTERVAL_SECONDS)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=records[0].keys(),
        )
        writer.writeheader()
        writer.writerows(records)

    success_rate = success_count / TOTAL_RUNS * 100

    print("\n" + "=" * 55)
    print("腾讯实时行情稳定性测试结果")
    print("=" * 55)
    print(f"总次数：{TOTAL_RUNS}")
    print(f"成功次数：{success_count}")
    print(f"失败次数：{failure_count}")
    print(f"成功率：{success_rate:.2f}%")

    if response_times:
        print(
            f"平均响应时间："
            f"{statistics.mean(response_times):.2f}ms"
        )
        print(
            f"中位响应时间："
            f"{statistics.median(response_times):.2f}ms"
        )
        print(
            f"最快响应时间："
            f"{min(response_times):.2f}ms"
        )
        print(
            f"最慢响应时间："
            f"{max(response_times):.2f}ms"
        )

    print(f"明细文件：{OUTPUT_PATH}")

    if success_rate < 98:
        raise SystemExit(
            f"稳定性未达标：成功率仅{success_rate:.2f}%"
        )


if __name__ == "__main__":
    main()
