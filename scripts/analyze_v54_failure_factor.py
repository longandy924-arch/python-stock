from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

file = BASE_DIR / "records" / "v52_candidate_records.csv"

if not file.exists():
    print("暂无交易记录")
    exit()

df = pd.read_csv(file)

done = df[df["是否成功"].notna()].copy()

if len(done) == 0:
    print("暂无完成交易")
    exit()

print("===== V54失败因子分析 =====")

fail = done[done["是否成功"]==0]
success = done[done["是否成功"]==1]

print("成功样本:", len(success))
print("失败样本:", len(fail))

cols=[
    "single_pick_score",
    "gain_4d",
    "gain_5d",
    "amount",
    "circ_mv",
    "turnover_pct"
]

for c in cols:
    if c in done.columns:
        print("\n指标:",c)
        print("成功均值:",round(success[c].mean(),4))
        print("失败均值:",round(fail[c].mean(),4))

print("\n分析完成")
