from pathlib import Path
import sqlite3
import pandas as pd
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]

csv_file = BASE_DIR / "records" / "v52_candidate_records.csv"
db_file = BASE_DIR / "records" / "v52_trade.db"

if not csv_file.exists():
    print("暂无CSV交易记录")
    raise SystemExit

df = pd.read_csv(csv_file)

conn = sqlite3.connect(db_file)

df["create_time"] = datetime.now()

df.to_sql(
    "trade_records",
    conn,
    if_exists="replace",
    index=False
)

conn.close()

print("V52 CSV同步数据库完成")
print(f"同步数量: {len(df)}")
print(db_file)
