from pathlib import Path
from datetime import datetime
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
LIVE_DIR = BASE_DIR / "output" / "live"
RECORD_DIR = BASE_DIR / "records"
RECORD_FILE = RECORD_DIR / "v52_live_trade_records.csv"

RECORD_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(
    LIVE_DIR.glob("v52_live_pick_*.csv"),
    key=lambda x: x.stat().st_mtime,
    reverse=True,
)

today = datetime.now().strftime("%Y-%m-%d")
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

columns = [
    "记录日期",
    "记录时间",
    "股票代码",
    "股票名称",
    "推荐价格",
    "当日涨幅",
    "近4日涨幅",
    "近5日涨幅",
    "流通市值",
    "实时换手率",
    "V52评分",
    "执行状态",
    "次日最高价",
    "次日最高收益率",
    "次日收盘价",
    "次日收盘收益率",
    "是否成功",
    "备注",
]

if RECORD_FILE.exists():
    records = pd.read_csv(RECORD_FILE)
else:
    records = pd.DataFrame(columns=columns)

# 避免同一天重复记录
if not records.empty and today in records["记录日期"].astype(str).values:
    print(f"今日 {today} 已有记录，不重复写入。")
    raise SystemExit

if not files:
    row = {
        "记录日期": today,
        "记录时间": now,
        "股票代码": "",
        "股票名称": "",
        "推荐价格": "",
        "当日涨幅": "",
        "近4日涨幅": "",
        "近5日涨幅": "",
        "流通市值": "",
        "实时换手率": "",
        "V52评分": "",
        "执行状态": "空仓",
        "次日最高价": "",
        "次日最高收益率": "",
        "次日收盘价": "",
        "次日收盘收益率": "",
        "是否成功": "",
        "备注": "当日无V52候选文件",
    }
else:
    df = pd.read_csv(files[0])

    if df.empty:
        row = {
            "记录日期": today,
            "记录时间": now,
            "股票代码": "",
            "股票名称": "",
            "推荐价格": "",
            "当日涨幅": "",
            "近4日涨幅": "",
            "近5日涨幅": "",
            "流通市值": "",
            "实时换手率": "",
            "V52评分": "",
            "执行状态": "空仓",
            "次日最高价": "",
            "次日最高收益率": "",
            "次日收盘价": "",
            "次日收盘收益率": "",
            "是否成功": "",
            "备注": "V52结果为空",
        }
    else:
        r = df.iloc[0]
        row = {
            "记录日期": today,
            "记录时间": now,
            "股票代码": r.get("ts_code", r.get("code", "")),
            "股票名称": r.get("name", ""),
            "推荐价格": r.get("price", ""),
            "当日涨幅": r.get("pct_chg", ""),
            "近4日涨幅": r.get("gain_4d", ""),
            "近5日涨幅": r.get("gain_5d", ""),
            "流通市值": r.get("circ_mv", ""),
            "实时换手率": r.get("turnover_pct", ""),
            "V52评分": r.get("single_pick_score", ""),
            "执行状态": "已推荐",
            "次日最高价": "",
            "次日最高收益率": "",
            "次日收盘价": "",
            "次日收盘收益率": "",
            "是否成功": "",
            "备注": f"来源文件: {files[0].name}",
        }

records = pd.concat([records, pd.DataFrame([row])], ignore_index=True)
records.to_csv(RECORD_FILE, index=False, encoding="utf-8-sig")

print("V52实盘记录已写入：")
print(RECORD_FILE)
print(pd.DataFrame([row]).to_string(index=False))
