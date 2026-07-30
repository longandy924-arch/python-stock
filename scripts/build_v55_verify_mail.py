from pathlib import Path
from datetime import datetime
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
RECORD_FILE = BASE_DIR / "records" / "v55_selected_records.csv"

print("【V55/V56次日验证日报】")
print()

if not RECORD_FILE.exists():
    print("暂无选股记录。")
    print()
    print("生成时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    raise SystemExit

df = pd.read_csv(RECORD_FILE, dtype=str)

if df.empty:
    print("选股记录表为空。")
    print()
    print("生成时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    raise SystemExit

today = datetime.now().strftime("%Y%m%d")

verified = df[df["verify_status"].astype(str) == "已验证"].copy()
today_verified = df[df.get("verify_date", "").astype(str) == today].copy()
pending = df[df["verify_status"].astype(str) != "已验证"].copy()

print("统计汇总：")
print(f"累计选股记录：{len(df)}")
print(f"已验证：{len(verified)}")
print(f"待验证：{len(pending)}")

if len(verified) > 0:
    success_rate = (verified["success"].astype(str) == "成功").mean() * 100
    print(f"累计成功率：{success_rate:.2f}%")

print()

if len(today_verified) > 0:
    print("今日验证结果：")
    cols = [
        "selection_date", "signal_level", "ts_code", "name", "price",
        "next_trade_date", "next_high", "next_high_return",
        "next_close", "next_close_return", "success"
    ]
    cols = [c for c in cols if c in today_verified.columns]
    print(today_verified[cols].to_string(index=False))
else:
    print("今日暂无新增验证结果。")
    print("说明：可能今日没有到达次日验证条件，或昨日没有选出股票。")

print()

print("最近20条记录：")
cols = [
    "selection_date", "signal_level", "ts_code", "name", "price",
    "verify_status", "next_high_return", "next_close_return", "success"
]
cols = [c for c in cols if c in df.columns]
print(df.tail(20)[cols].to_string(index=False))

print()
print("记录文件：records/v55_selected_records.csv")
print("生成时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
