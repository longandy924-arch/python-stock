def market_type(ts_code):

    code = ts_code.split(".")[0]

    if code.startswith(("688","689")):
        return "科创板"

    if code.startswith(("8","9")):
        return "北交所"

    if code.startswith(("300","301")):
        return "创业板"

    return "主板"


def can_trade(ts_code):

    return market_type(ts_code) not in [
        "科创板",
        "北交所"
    ]


def market_priority(ts_code):

    m = market_type(ts_code)

    if m == "主板":
        return 0

    if m == "创业板":
        return 1

    return 9
