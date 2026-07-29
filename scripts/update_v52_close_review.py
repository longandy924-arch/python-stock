from pathlib import Path
import pandas as pd
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]

record_file = BASE_DIR / "records" / "v52_live_trade_records.csv"
review_file = BASE_DIR / "records" / "v52_live_review_report.csv"

if not record_file.exists():
    print("没有交易记录")
    raise SystemExit

df = pd.read_csv(record_file)

pending = df[
    (df["执行状态"] == "已推荐") &
    (df["次日最高价"].isna())
].copy()

if len(pending) == 0:
    print("没有待复盘交易")
    raise SystemExit

print("待复盘数量:", len(pending))

# 当前先建立结构，行情接口下一步接入
for i in pending.index:
    df.loc[i, "备注"] = "等待行情更新"

df.to_csv(
    record_file,
    index=False,
    encoding="utf-8-sig"
)

print("V52.2复盘结构更新完成")
print("时间:", datetime.now())

