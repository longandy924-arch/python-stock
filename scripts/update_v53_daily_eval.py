from pathlib import Path
import pandas as pd
import sqlite3
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]

record_file = BASE_DIR / "records" / "v52_candidate_records.csv"
db_file = BASE_DIR / "records" / "v52_trade.db"

if not record_file.exists():
    print("暂无候选记录")
    exit()

df = pd.read_csv(record_file)

pending = df[df["是否成功"].isna()]

print("待评价数量:", len(pending))

if len(pending)==0:
    print("暂无需要评价交易")
    exit()

conn = sqlite3.connect(db_file)

pending.to_sql(
    "pending_eval",
    conn,
    if_exists="replace",
    index=False
)

conn.close()

print("V53评价任务更新完成")
