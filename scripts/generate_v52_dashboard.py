from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

record = BASE_DIR / "records" / "v52_live_trade_records.csv"
out = BASE_DIR / "reports" / "v52_dashboard.csv"

if not record.exists():
    print("暂无交易记录")
    raise SystemExit

df = pd.read_csv(record)

done = df[df["是否成功"].notna()].copy()

if len(done)==0:
    print("暂无完成交易")
    raise SystemExit


result = pd.DataFrame([
    {
        "指标":"累计交易次数",
        "数值":len(done)
    },
    {
        "指标":"成功率",
        "数值":done["是否成功"].mean()
    },
    {
        "指标":"平均次日最高收益",
        "数值":done["次日最高收益率"].mean()
    },
    {
        "指标":"平均次日收盘收益",
        "数值":done["次日收盘收益率"].mean()
    },
    {
        "指标":"平均V52评分",
        "数值":done["V52评分"].mean()
    }
])

result.to_csv(
    out,
    index=False,
    encoding="utf-8-sig"
)

print("V52.9监控面板生成完成")
print(out)
print(result)

