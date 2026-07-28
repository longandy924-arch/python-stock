"""
A股交易日判断。

优先使用 akshare 交易日历；
如果 akshare 不可用，则停止选股并返回异常，避免节假日误运行。
"""

from __future__ import annotations

import sys
from datetime import datetime


def main() -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = datetime.now().weekday()  # 周一=0，周日=6

    if weekday >= 5:
        print(f"今日 {today} 是周末，非A股交易日。")
        sys.exit(1)

    try:
        import akshare as ak
    except Exception as exc:
        print(f"无法导入 akshare，不能判断交易日，停止选股。错误: {exc}")
        sys.exit(2)

    try:
        cal = ak.tool_trade_date_hist_sina()
    except Exception as exc:
        print(f"无法获取A股交易日历，停止选股。错误: {exc}")
        sys.exit(2)

    if "trade_date" not in cal.columns:
        print(f"交易日历缺少 trade_date 字段，停止选股。字段: {cal.columns.tolist()}")
        sys.exit(2)

    dates = set(cal["trade_date"].astype(str).str[:10].tolist())

    if today in dates:
        print(f"今日 {today} 是A股交易日。")
        sys.exit(0)

    print(f"今日 {today} 不是A股交易日。")
    sys.exit(1)


if __name__ == "__main__":
    main()
