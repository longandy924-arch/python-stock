from pathlib import Path
from datetime import datetime
import sys
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
LIVE_DIR = BASE_DIR / "output" / "live"
REJECT_DIR = LIVE_DIR / "rejected"
RECORD_DIR = BASE_DIR / "records"
RECORD_DIR.mkdir(parents=True, exist_ok=True)

OUT = RECORD_DIR / "v55_selected_records.csv"

level = sys.argv[1] if len(sys.argv) > 1 else "A"

files = list(LIVE_DIR.glob("v52_live_pick_*.csv"))
files += list(REJECT_DIR.glob("v52_live_pick_*.csv"))
files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)

if not files:
    print("未找到候选文件，无法记录")
    raise SystemExit(1)

latest = files[0]
df = pd.read_csv(latest)

if df.empty:
    print("候选文件为空，无法记录")
    raise SystemExit(1)

row = df.iloc[0]

def val(*names, default=""):
    for n in names:
        if n in row.index and pd.notna(row[n]):
            return row[n]
    return default

now = datetime.now()

record = {
    "selection_date": now.strftime("%Y%m%d"),
    "selection_time": now.strftime("%H:%M:%S"),
    "signal_level": level,
    "ts_code": val("ts_code", "股票代码", "code"),
    "name": val("name", "股票名称"),
    "price": val("price", "当前价格"),
    "pct_chg": val("pct_chg", "当日涨幅"),
    "gain_4d": val("gain_4d", "近4日涨幅"),
    "gain_5d": val("gain_5d", "近5日涨幅"),
    "amount": val("amount", "成交额"),
    "circ_mv": val("circ_mv", "流通市值"),
    "turnover_pct": val("turnover_pct", "实时换手率估算", "实时换手率"),
    "score": val("single_pick_score", "V52评分"),
    "source_file": latest.name,
    "verify_status": "待验证",
    "verify_date": "",
    "next_trade_date": "",
    "next_high": "",
    "next_close": "",
    "next_high_return": "",
    "next_close_return": "",
    "success": "",
}

new_df = pd.DataFrame([record])

if OUT.exists():
    old = pd.read_csv(OUT, dtype=str)
else:
    old = pd.DataFrame()

if not old.empty:
    exists = (
        (old["selection_date"].astype(str) == str(record["selection_date"])) &
        (old["ts_code"].astype(str) == str(record["ts_code"])) &
        (old["signal_level"].astype(str) == str(record["signal_level"]))
    ).any()

    if exists:
        print("今日该股票已记录，不重复写入")
        raise SystemExit(0)

    out_df = pd.concat([old, new_df], ignore_index=True)
else:
    out_df = new_df

out_df.to_csv(OUT, index=False, encoding="utf-8-sig")

print("V55/V56选股记录已写入：", OUT)
print("级别:", level)
print("股票:", record["ts_code"], record["name"])
print("价格:", record["price"])
