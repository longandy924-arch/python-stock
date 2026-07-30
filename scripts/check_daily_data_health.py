from pathlib import Path
import pandas as pd
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR/"data"/"daily"

files=list(DATA_DIR.glob("*.csv"))

bad=[]
latest=[]

for f in files:
    try:
        df=pd.read_csv(f)

        if "trade_date" not in df.columns:
            bad.append(f.name)
            continue

        latest.append(
            str(df["trade_date"].max())
        )

    except:
        bad.append(f.name)


print("股票文件数量:",len(files))

if latest:
    print(
        "最新交易日期:",
        max(latest)
    )

print(
    "异常文件:",
    len(bad)
)

if bad:
    print(bad[:10])

