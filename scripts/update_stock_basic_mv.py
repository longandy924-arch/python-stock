from pathlib import Path
from datetime import datetime
import pandas as pd
import tushare as ts
import os


BASE_DIR = Path(__file__).resolve().parents[1]


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


def main():

    pro = get_pro()

    today = datetime.now().strftime("%Y%m%d")

    print("更新流通市值:", today)


    df = pro.daily_basic(
        trade_date=today,
        fields=
        "ts_code,trade_date,close,total_mv,circ_mv"
    )


    if df.empty:
        raise RuntimeError(
            "没有获取到daily_basic数据"
        )


    out = BASE_DIR / "data" / "stock_basic_mv.csv"


    df.to_csv(
        out,
        index=False,
        encoding="utf-8-sig"
    )


    print(
        "更新完成:",
        len(df),
        "只股票"
    )

    print(
        "文件:",
        out
    )


if __name__=="__main__":
    main()
