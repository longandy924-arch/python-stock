from pathlib import Path
import pandas as pd
import tushare as ts

BASE_DIR = Path(__file__).resolve().parents[1]

file = BASE_DIR / "records" / "v52_candidate_records.csv"

if not file.exists():
    print("暂无交易记录")
    raise SystemExit

df = pd.read_csv(file)

need = df[df["next_high"].isna()].copy()

if len(need) == 0:
    print("暂无需要回填记录")
    raise SystemExit


pro = ts.pro_api()

for idx,row in need.iterrows():

    ts_code = row["ts_code"]
    buy_date = str(row["date"])

    daily = pro.daily(
        ts_code=ts_code,
        start_date=buy_date,
        limit=5
    )

    daily = daily.sort_values("trade_date")

    if len(daily) < 2:
        continue

    next_day = daily.iloc[1]

    buy_price = float(row["price"])

    high = float(next_day["high"])
    close = float(next_day["close"])

    df.loc[idx,"next_high"] = high
    df.loc[idx,"next_close"] = close

    df.loc[idx,"next_high_return"] = high / buy_price - 1
    df.loc[idx,"next_close_return"] = close / buy_price - 1

    df.loc[idx,"是否成功"] = (
        df.loc[idx,"next_high_return"] >= 0.025
    )


df.to_csv(
    file,
    index=False,
    encoding="utf-8-sig"
)

print("V52次日行情回填完成")
print(df.tail())

