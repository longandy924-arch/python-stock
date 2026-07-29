from pathlib import Path
import sqlite3
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

db = BASE_DIR / "records" / "v52_trade.db"

conn = sqlite3.connect(db)

df = pd.read_sql(
    "select * from trade_records",
    conn
)

# 字段兼容
rename_map = {
    "是否成功": "success",
    "次日最高收益率": "next_high_return",
    "次日收盘收益率": "next_close_return"
}

df.rename(
    columns=rename_map,
    inplace=True
)

conn.close()

if len(df) == 0:
    print("暂无交易数据")
    raise SystemExit

result = {
    "累计记录": len(df),
    "已完成交易": int(df["success"].notna().sum()),
    "成功率": round(df["success"].mean()*100,2)
        if df["success"].notna().sum()>0 else None,
    "平均最高收益": round(df["next_high_return"].mean()*100,2)
        if "next_high_return" in df.columns else None,
    "平均收盘收益": round(df["next_close_return"].mean()*100,2)
        if "next_close_return" in df.columns else None
}

print(pd.DataFrame([result]))

out = BASE_DIR / "reports" / "v52_db_summary.csv"
pd.DataFrame([result]).to_csv(
    out,
    index=False,
    encoding="utf-8-sig"
)

print(out)
