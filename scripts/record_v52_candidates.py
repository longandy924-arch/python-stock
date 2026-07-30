from pathlib import Path
import pandas as pd
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]

source = BASE_DIR / "output" / "live"
target = BASE_DIR / "records" / "v52_candidate_records.csv"

files = sorted(source.glob("v52_live_pick_*.csv"))

if not files:
    print("暂无候选文件")
    raise SystemExit

latest = files[-1]

df = pd.read_csv(latest)

df["记录时间"] = datetime.now()

if "排名" not in df.columns:
    df["排名"] = range(1, len(df)+1)

if target.exists():
    old = pd.read_csv(target)
    df = pd.concat([old, df], ignore_index=True)

df.to_csv(
    target,
    index=False,
    encoding="utf-8-sig"
)

print("V52候选池记录完成")
print(target)
print("记录数量:", len(df))
