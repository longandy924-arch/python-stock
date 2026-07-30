from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "daily"

files = list(DATA_DIR.glob("*.csv"))

bad = []
latest = []
small = []

required = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount"
]

for f in files:
    try:
        df = pd.read_csv(f)

        date_col = None

        if "trade_date" in df.columns:
            date_col = "trade_date"
        elif "date" in df.columns:
            date_col = "date"

        if date_col is None:
            bad.append(f.name)
            continue

        for c in required:
            if c not in df.columns:
                bad.append(f.name)
                break

        if len(df) < 100:
            small.append(f.name)

        latest.append(str(df[date_col].max()))

    except Exception:
        bad.append(f.name)

print("股票文件数量:", len(files))

print("最新交易日期:", max(latest) if latest else None)

print("字段异常:", len(bad))
if bad:
    print(bad[:10])

print("数据过少:", len(small))
if small:
    print(small[:10])
