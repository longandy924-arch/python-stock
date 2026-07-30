from pathlib import Path
import pandas as pd
import sys
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
LIVE_DIR = BASE_DIR / "output" / "live"
REJECT_DIR = LIVE_DIR / "rejected"
REJECT_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(LIVE_DIR.glob("v52_live_pick_*.csv"))

if not files:
    print("暂无V52候选文件")
    sys.exit(1)

latest = files[-1]
df = pd.read_csv(latest)

if len(df) == 0:
    print("候选文件为空")
    sys.exit(1)

row = df.iloc[0]

def pick_col(*names):
    for n in names:
        if n in df.columns:
            return n
    return None

code_col = pick_col("股票代码", "code", "ts_code")
name_col = pick_col("股票名称", "name")
gain4_col = pick_col("近4日涨幅", "gain_4d")
gain5_col = pick_col("近5日涨幅", "gain_5d")
turn_col = pick_col("实时换手率估算", "turnover_pct")
score_col = pick_col("V52评分", "single_pick_score", "score")

code = str(row[code_col]) if code_col else "UNKNOWN"
name = str(row[name_col]) if name_col else "UNKNOWN"

def to_float(col):
    if not col:
        return None
    try:
        return float(row[col])
    except Exception:
        return None

gain4 = to_float(gain4_col)
gain5 = to_float(gain5_col)
turnover = to_float(turn_col)
score = to_float(score_col)

reasons = []

# 注意：这里不排除创业板，只排除过热候选
# 当前规则目的：避免高位加速、高换手、追涨过热
if gain4 is not None and gain4 > 25:
    reasons.append(f"近4日涨幅过高：{gain4:.2f}% > 25%")

if gain5 is not None and gain5 > 30:
    reasons.append(f"近5日涨幅过高：{gain5:.2f}% > 30%")

if turnover is not None and turnover > 8:
    reasons.append(f"实时换手率过高：{turnover:.2f}% > 8%")

if gain4 is not None and turnover is not None:
    if gain4 > 20 and turnover > 6:
        reasons.append(f"高涨幅叠加高换手：近4日{gain4:.2f}%，换手{turnover:.2f}%")

if gain5 is not None and turnover is not None:
    if gain5 > 25 and turnover > 6:
        reasons.append(f"5日加速叠加高换手：近5日{gain5:.2f}%，换手{turnover:.2f}%")

if reasons:
    reject_file = REJECT_DIR / latest.name
    latest.rename(reject_file)

    print("V52候选被过热过滤器拒绝")
    print("股票代码:", code)
    print("股票名称:", name)
    print("V52评分:", score)
    print("拒绝原因:")
    for r in reasons:
        print("-", r)
    print("已移入:", reject_file)
    sys.exit(1)

print("V52候选因子匹配校验通过")
print("股票代码:", code)
print("股票名称:", name)
print("近4日涨幅:", gain4)
print("近5日涨幅:", gain5)
print("实时换手率:", turnover)
print("V52评分:", score)
sys.exit(0)
