from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parents[1]

db = BASE_DIR / "records" / "v52_trade.db"

conn = sqlite3.connect(db)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS trade_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT,
    ts_code TEXT,
    name TEXT,
    price REAL,
    single_pick_score REAL,
    gain_4d REAL,
    gain_5d REAL,
    pct_chg REAL,
    circ_mv REAL,
    turnover_pct REAL,
    next_high_return REAL,
    next_close_return REAL,
    success INTEGER,
    create_time TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS daily_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary_date TEXT,
    sample_count INTEGER,
    success_rate REAL,
    avg_high_return REAL,
    avg_close_return REAL,
    avg_score REAL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS factor_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factor_name TEXT,
    success_avg REAL,
    fail_avg REAL,
    analysis_date TEXT
)
""")

conn.commit()
conn.close()

print("V52数据库初始化完成")
print(db)
