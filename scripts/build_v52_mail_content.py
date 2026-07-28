from pathlib import Path
import pandas as pd
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]

files = sorted(
    (BASE_DIR / "output" / "live").glob("v52_live_pick_*.csv"),
    key=lambda x: x.stat().st_mtime,
    reverse=True
)

if not files:
    print("V52今日无候选")
    raise SystemExit

df = pd.read_csv(files[0])

row = df.iloc[0]

print("【V52今日唯一候选】")
print()
print(f"股票：{row.get('name','')}")
print(f"代码：{row.get('ts_code',row.get('code',''))}")
print()
print(f"当前价：{row.get('price','')}")
print(f"当日涨幅：{row.get('pct_chg','')}")
print(f"近4日涨幅：{row.get('gain_4d','')}")
print(f"近5日涨幅：{row.get('gain_5d','')}")
print(f"流通市值：{row.get('circ_mv','')}")
print(f"实时换手率：{row.get('turnover_pct','')}")
print(f"V52评分：{row.get('single_pick_score','')}")
print()
print("执行：14:40附近买入")
print("纪律：次日无论涨跌坚决卖出")
print()
print("生成时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
