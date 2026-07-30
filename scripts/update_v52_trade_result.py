from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

file = BASE_DIR / "records" / "v52_candidate_records.csv"

if not file.exists():
    print("暂无交易记录")
    raise SystemExit

df = pd.read_csv(file)

required = [
    "next_high",
    "next_close",
    "next_high_return",
    "next_close_return",
    "是否成功"
]

for c in required:
    if c not in df.columns:
        df[c] = None

df.to_csv(
    file,
    index=False,
    encoding="utf-8-sig"
)

print("V52交易结果字段初始化完成")
print(df.columns.tolist())
