from datetime import datetime
import sys

today = datetime.now().strftime("%Y%m%d")

try:
    import tushare as ts

    pro = ts.pro_api()

    df = pro.trade_cal(
        exchange="SSE",
        start_date=today,
        end_date=today
    )

    if len(df) == 0:
        print("交易日判断失败")
        sys.exit(2)

    if int(df.iloc[0]["is_open"]) == 1:
        print("交易日")
        sys.exit(0)
    else:
        print("非交易日")
        sys.exit(1)

except Exception as e:
    print("交易日判断异常:", e)
    sys.exit(2)
