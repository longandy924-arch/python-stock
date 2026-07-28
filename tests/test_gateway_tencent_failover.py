"""验证 Gateway 从失败数据源切换到腾讯。"""

import pandas as pd

from data_source.providers.base import RealtimeDataProvider
from data_source.providers.tencent_provider import (
    TencentRealtimeProvider,
)
from data_source.realtime_gateway import RealtimeGateway


class FailedProvider(RealtimeDataProvider):
    provider_name = "forced_failure"

    def is_available(self) -> bool:
        return True

    def get_quotes(self) -> pd.DataFrame:
        raise RuntimeError("模拟首选数据源故障")


if __name__ == "__main__":
    gateway = RealtimeGateway(
        providers=[
            FailedProvider(),
            TencentRealtimeProvider(
                ts_codes=[
                    "000001.SZ",
                    "600000.SH",
                ]
            ),
        ],
        cache_path="data/cache/tencent_test_quotes.csv",
        log_path="logs/realtime_test.log",
    )

    quotes = gateway.get_realtime_quotes()

    assert not quotes.empty
    assert gateway.current_source == "tencent"
    assert gateway.switched is True
    assert gateway.stock_count >= 1

    print("Gateway真实自动切换成功")
    print(f"当前Provider：{gateway.current_source}")
    print(f"是否发生切换：{gateway.switched}")
    print(f"响应时间(ms)：{gateway.response_time_ms}")
    print(f"返回股票数量：{gateway.stock_count}")
