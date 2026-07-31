from pathlib import Path
from datetime import datetime
import pandas as pd
import tushare as ts
import os

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "daily"

def get_pro():
    token = os.getenv("TUSHARE_TOKEN")

    if not token:
        for p in [
            BASE_DIR / "config" / "tushare_token.txt",
            BASE_DIR / ".tushare_token"
        ]:
            if p.exists():
                token = p.read_text().strip()
                break

    if not token:
        raise RuntimeError("未找到Tushare token")

    ts.set_token(token)
    return ts.pro_api()


def update_one(pro, ts_code):
    file = DATA_DIR / f"{ts_code}.csv"

    if file.exists():
        old = pd.read_csv(file)
        date_col = "trade_date" if "trade_date" in old.columns else "date"
        last_date = str(old[date_col].max())
    else:
        old = pd.DataFrame()
        last_date = "20100101"

    today = datetime.now().strftime("%Y%m%d")

    df = pro.daily(
        ts_code=ts_code,
        start_date=last_date,
        end_date=today
    )

    if df.empty:
        return 0

    result = pd.concat(
        [old, df],
        ignore_index=True
    )

    result = result.drop_duplicates(
        subset=[date_col],
        keep="last"
    )

    result = result.sort_values(date_col)

    result.to_csv(
        file,
        index=False,
        encoding="utf-8-sig"
    )

    return len(df)


def main():
    pro = get_pro()

    files = list(DATA_DIR.glob("*.csv"))

    total = 0

    for i,f in enumerate(files,1):

        code=f.stem

        try:
            total += update_one(pro,code)
        except Exception as e:
            print(code,e)

        if i % 500 == 0:
            print(f"更新进度 {i}/{len(files)}")

    print("新增日线:",total)


if __name__=="__main__":
    main()
