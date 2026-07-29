from pathlib import Path
import pandas as pd
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]

record_file = BASE_DIR / "records" / "v52_live_trade_records.csv"
result_file = BASE_DIR / "records" / "v52_live_review_report.csv"

if not record_file.exists():
    print("暂无交易记录")
    raise SystemExit

df = pd.read_csv(record_file)

if "是否成功" not in df.columns:
    df["是否成功"] = ""

completed = df[df["次日最高价"].notna()].copy()

if len(completed) == 0:
    print("暂无完成交易样本")
    raise SystemExit

completed["是否成功"] = (
    completed["次日最高价"].astype(float)
    >= completed["推荐价格"].astype(float) * 1.025
)

completed.to_csv(
    result_file,
    index=False,
    encoding="utf-8-sig"
)

success = completed["是否成功"].sum()
total = len(completed)

print("==============================")
print("V52.1 实盘复盘")
print("==============================")
print(f"样本数量: {total}")
print(f"成功数量: {success}")
print(f"成功率: {success/total:.2%}")
print(f"报告文件: {result_file}")
