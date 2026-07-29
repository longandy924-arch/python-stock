from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

file = BASE_DIR / "records" / "v52_live_trade_records.csv"
out = BASE_DIR / "reports" / "v52_weight_analysis.csv"

if not file.exists():
    print("暂无交易记录")
    raise SystemExit

df = pd.read_csv(file)

df = df[df["是否成功"].notna()].copy()

if len(df)==0:
    print("暂无完成样本")
    raise SystemExit


factors = [
    "近4日涨幅",
    "近5日涨幅",
    "当日涨幅",
    "成交额",
    "V52评分"
]


result=[]

for f in factors:
    if f in df.columns:
        result.append({
            "因子":f,
            "成功样本平均":df[df["是否成功"]==True][f].mean(),
            "失败样本平均":df[df["是否成功"]==False][f].mean()
        })


pd.DataFrame(result).to_csv(
    out,
    index=False,
    encoding="utf-8-sig"
)

print("V52.8权重分析完成")
print(out)

