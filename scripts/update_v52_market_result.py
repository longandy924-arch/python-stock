from pathlib import Path
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parents[1]

record_file = BASE_DIR / "records" / "v52_live_trade_records.csv"

if not record_file.exists():
    print("没有交易记录")
    raise SystemExit

df = pd.read_csv(record_file)

pending = df[
    (df["执行状态"] == "已推荐") &
    (df["次日最高价"].isna())
].copy()

if len(pending) == 0:
    print("暂无待更新记录")
    raise SystemExit

pro = ts.pro_api()

for idx, row in pending.iterrows():

    code = row["股票代码"]
    buy_price = float(row["推荐价格"])

    start = (
        datetime.strptime(row["记录日期"], "%Y-%m-%d")
        + timedelta(days=1)
    ).strftime("%Y%m%d")

    end = start

    try:
        data = pro.daily(
            ts_code=code,
            start_date=start,
            end_date=end
        )

        if len(data) == 0:
            continue

        high = float(data.iloc[0]["high"])
        close = float(data.iloc[0]["close"])

        df.loc[idx, "次日最高价"] = high
        df.loc[idx, "次日收盘价"] = close

        df.loc[idx, "次日最高收益率"] = (
            high / buy_price - 1
        )

        df.loc[idx, "次日收盘收益率"] = (
            close / buy_price - 1
        )

        df.loc[idx, "是否成功"] = (
            high >= buy_price * 1.025
        )

        df.loc[idx, "备注"] = "Tushare自动回填"

        print(code, "更新完成")

    except Exception as e:
        print(code, "失败:", e)


df.to_csv(
    record_file,
    index=False,
    encoding="utf-8-sig"
)

print("V52.3行情回填完成")
