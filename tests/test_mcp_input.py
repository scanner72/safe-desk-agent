import json
from pathlib import Path

import pytest

from safe_desk.mcp_input import (
    MCP_ENDPOINT,
    load_json_payload,
    load_live_quote,
    parse_balance_payload,
    parse_price_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def test_parse_binance_style_ticker():
    price = parse_price_payload(
        {
            "symbol": "btcusdt",
            "lastPrice": "102450.00",
            "bidPrice": "102448.50",
            "askPrice": "102451.20",
            "priceChangePercent": "1.80",
        }
    )
    assert price.symbol == "BTCUSDT"
    assert price.last == 102450.0
    assert price.bid == pytest.approx(102448.50)
    assert price.change_pct == pytest.approx(1.80)


def test_parse_wrapped_result_and_list():
    price = parse_price_payload({"result": {"data": [{"s": "ETHUSDT", "c": "4000"}]}})
    assert price.symbol == "ETHUSDT"
    assert price.last == 4000.0


def test_parse_agentic_balances():
    bal = parse_balance_payload(
        {
            "account": "agentic",
            "balances": [
                {"asset": "USDT", "free": "1000.00", "locked": "0"},
                {"asset": "BTC", "free": "0", "locked": "0"},
            ],
        }
    )
    assert bal.quote_asset == "USDT"
    assert bal.free == 1000.0
    assert bal.equity == 1000.0
    assert bal.account == "agentic"


def test_parse_flat_quote_map():
    bal = parse_balance_payload({"USDT": {"free": 250, "locked": 10}})
    assert bal.free == 250
    assert bal.locked == 10
    assert bal.equity == 260


def test_repo_example_json_merges():
    quote = load_live_quote(
        price_source=ROOT / "examples" / "mcp-price.json",
        balance_source=ROOT / "examples" / "mcp-balance.json",
    )
    assert quote.last == 102450.0
    assert quote.equity == 1000.0
    assert quote.symbol == "BTCUSDT"
    assert MCP_ENDPOINT in quote.notes[0]
    assert "API keys" in quote.notes[0]


def test_load_json_payload_raw_string():
    payload = load_json_payload('{"lastPrice": "1.5", "symbol": "SOLUSDT"}')
    assert parse_price_payload(payload).last == 1.5


def test_rejects_empty_price():
    with pytest.raises(ValueError):
        parse_price_payload({"symbol": "BTCUSDT"})


def test_example_files_are_not_secrets():
    for name in ("mcp-price.json", "mcp-balance.json"):
        text = (ROOT / "examples" / name).read_text(encoding="utf-8")
        blob = json.loads(text)
        dumped = json.dumps(blob).lower()
        assert "api_key" not in dumped
        assert "apikey" not in dumped
        assert "secret_key" not in dumped
        assert "apiKey" not in text
