from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

file = BASE_DIR / "records" / "v52_candidate_records.csv"

if not file.exists():
    print("暂无交易记录")
    exit()

df = pd.read_csv(file)

done = df[df["是否成功"].notna()].copy()

print("===== V53策略监控 =====")
print("总记录:", len(df))
print("已完成:", len(done))

if len(done) > 0:
    print("成功率:", round(done["是否成功"].mean()*100,2), "%")
    print("平均最高收益:",
          round(done["next_high_return"].mean()*100,2), "%")
    print("平均收盘收益:",
          round(done["next_close_return"].mean()*100,2), "%")

    print("\n最近20笔:")
    print(done.tail(20)[[
        "date",
        "name",
        "single_pick_score",
        "next_high_return",
        "是否成功"
    ]])

