"""指标模块基础验证。"""

import numpy as np
import pandas as pd

from strategy.indicators import calculate_indicators, validate_no_future_data


def build_test_data() -> pd.DataFrame:
    size = 30
    close = np.linspace(10, 13, size)

    return pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=size),
            "open": close - 0.10,
            "high": close + 0.30,
            "low": close - 0.30,
            "close": close,
            "vol": np.linspace(100000, 160000, size),
        }
    )


if __name__ == "__main__":
    source = build_test_data()
    result = calculate_indicators(source)

    assert len(result) == len(source)
    assert result["ma5"].notna().sum() == 26
    assert result["ma10"].notna().sum() == 21
    assert result["ma20"].notna().sum() == 11
    assert result["close_strength"].between(0, 1).all()
    assert validate_no_future_data(source)

    print("指标计算测试成功")
    print("未来函数初步验证通过")
    print(result.tail(3).to_string(index=False))
