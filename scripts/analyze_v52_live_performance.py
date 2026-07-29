from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

file = BASE_DIR / "records" / "v52_candidate_records.csv"

if not file.exists():
    print("暂无交易记录")
    raise SystemExit

df = pd.read_csv(file)

done = df[df["是否成功"].notna()].copy()

if len(done) == 0:
    print("暂无完成交易样本")
    raise SystemExit

result = {
    "累计样本": len(done),
    "成功率": round(done["是否成功"].mean()*100,2),
    "平均次日最高收益": round(done["next_high_return"].mean()*100,2),
    "平均次日收盘收益": round(done["next_close_return"].mean()*100,2),
    "平均V52评分": round(done["single_pick_score"].mean(),3)
}

print(pd.DataFrame([result]))

out = BASE_DIR / "reports" / "v52_live_performance.csv"
pd.DataFrame([result]).to_csv(out,index=False,encoding="utf-8-sig")

print(out)
