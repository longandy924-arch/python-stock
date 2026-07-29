from pathlib import Path
import pandas as pd
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]

record_file = BASE_DIR / "records" / "v52_live_trade_records.csv"
report_file = BASE_DIR / "reports" / "v52_daily_report.md"

report_file.parent.mkdir(exist_ok=True)

if not record_file.exists():
    print("暂无交易记录")
    raise SystemExit

df = pd.read_csv(record_file)

done = df[df["是否成功"].notna()].copy()

if len(done) == 0:
    print("暂无完成复盘数据")
    raise SystemExit

success = done["是否成功"].astype(bool).sum()
total = len(done)

win_rate = success / total

avg_high = done["次日最高收益率"].astype(float).mean()

avg_close = done["次日收盘收益率"].astype(float).mean()

score_report = ""

if "V52评分" in done.columns:
    done["评分区间"] = pd.cut(
        done["V52评分"].astype(float),
        bins=[0,0.7,0.8,0.9,1],
        labels=["<0.7","0.7-0.8","0.8-0.9",">0.9"]
    )

    score_report = (
        "\n评分区间表现：\n\n"
        + done.groupby("评分区间", observed=False)["是否成功"]
        .agg(["count","sum"])
        .to_string()
    )

text = f"""
# V52每日实盘报告

生成时间：
{datetime.now()}

## 总体表现

交易次数：
{total}

成功次数：
{success}

成功率：
{win_rate:.2%}

平均次日最高收益：
{avg_high:.2%}

平均次日收盘收益：
{avg_close:.2%}

{score_report}

"""

report_file.write_text(
    text,
    encoding="utf-8"
)

print("V52报告生成完成")
print(report_file)

