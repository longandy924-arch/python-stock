"""EastMoney realtime quote client tests."""

from pathlib import Path
import sys
import unittest

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data_source.eastmoney_api import EastMoneyAPI, EastMoneyDataError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def get(self, url, params, timeout):
        self.calls.append(
            {
                "url": url,
                "page": params["pn"],
                "fid": params["fid"],
                "timeout": timeout,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def eastmoney_payload(rows, total=None):
    return {
        "data": {
            "total": len(rows) if total is None else total,
            "diff": rows,
        }
    }


class EastMoneyAPITest(unittest.TestCase):
    def test_realtime_quotes_normalizes_eastmoney_payload(self):
        session = FakeSession(
            [
                FakeResponse(
                    eastmoney_payload(
                        [
                            {
                                "f12": "1",
                                "f14": "平安银行",
                                "f2": "10.12",
                                "f3": "1.20",
                                "f4": "0.12",
                                "f5": "12345",
                                "f6": "4567890",
                                "f7": "2.34",
                                "f8": "0.56",
                                "f9": "-",
                                "f10": "1.10",
                                "f11": "0.20",
                                "f15": "10.30",
                                "f16": "9.98",
                                "f17": "10.00",
                                "f18": "10.00",
                                "f20": "100000000",
                                "f21": "80000000",
                                "f22": "0.01",
                                "f24": "5.50",
                                "f25": "8.80",
                            }
                        ]
                    )
                )
            ]
        )
        api = EastMoneyAPI(session=session, hosts=("mock-host",))

        quotes = api.get_realtime_quotes()

        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes.loc[0, "ts_code"], "000001.SZ")
        self.assertEqual(quotes.loc[0, "symbol"], "000001")
        self.assertEqual(quotes.loc[0, "name"], "平安银行")
        self.assertEqual(quotes.loc[0, "price"], 10.12)
        self.assertTrue(quotes.loc[0, "pe_dynamic"] != quotes.loc[0, "pe_dynamic"])
        self.assertEqual(session.calls[0]["fid"], "f12")

    def test_realtime_quotes_retries_after_connection_error(self):
        session = FakeSession(
            [
                requests.ConnectionError(
                    "Remote end closed connection without response"
                ),
                FakeResponse(
                    eastmoney_payload(
                        [
                            {
                                "f12": "600000",
                                "f14": "浦发银行",
                                "f2": "8.88",
                            }
                        ]
                    )
                ),
            ]
        )
        api = EastMoneyAPI(
            session=session,
            hosts=("mock-host",),
            retries=2,
            backoff=0,
        )

        quotes = api.get_realtime_quotes()

        self.assertEqual(len(session.calls), 2)
        self.assertEqual(quotes.loc[0, "ts_code"], "600000.SH")

    def test_get_quote_accepts_ts_code(self):
        session = FakeSession(
            [
                FakeResponse(
                    eastmoney_payload(
                        [
                            {
                                "f12": "000001",
                                "f14": "平安银行",
                                "f2": "10.12",
                            }
                        ]
                    )
                )
            ]
        )
        api = EastMoneyAPI(session=session, hosts=("mock-host",))

        quote = api.get_quote("000001.SZ")

        self.assertEqual(quote["name"], "平安银行")

    def test_empty_payload_raises_data_error(self):
        session = FakeSession([FakeResponse(eastmoney_payload([]))])
        api = EastMoneyAPI(session=session, hosts=("mock-host",))

        with self.assertRaises(EastMoneyDataError):
            api.get_realtime_quotes()


if __name__ == "__main__":
    unittest.main()
