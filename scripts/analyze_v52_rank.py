from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

file = BASE_DIR / "records" / "v52_candidate_records.csv"

if not file.exists():
    print("暂无候选记录")
    raise SystemExit

df = pd.read_csv(file)

if "是否成功" not in df.columns:
    print("等待交易结果")
    raise SystemExit

df = df[df["是否成功"].notna()].copy()

if len(df)==0:
    print("暂无完成样本")
    raise SystemExit


report = (
    df.groupby("排名")
    .agg(
        样本数=("是否成功","count"),
        成功数=("是否成功","sum"),
        成功率=("是否成功","mean"),
        平均最高收益=("次日最高收益率","mean")
    )
    .reset_index()
)

out = BASE_DIR / "reports" / "v52_rank_analysis.csv"

report.to_csv(
    out,
    index=False,
    encoding="utf-8-sig"
)

print("V52排名分析完成")
print(report)

