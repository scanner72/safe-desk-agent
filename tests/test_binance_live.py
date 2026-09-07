"""Live Binance public market data — mocked HTTP only. No secrets. No orders."""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from safe_desk.binance_live import (
    SOURCE,
    LiveMarketError,
    fetch_live_market,
    normalize_interval,
    normalize_limit,
    normalize_symbol,
)
from safe_desk.desk import Desk
from safe_desk.mcp_input import parse_klines_payload
from safe_desk.ohlcv import bars_to_csv, load_ohlcv, load_ohlcv_text
from safe_desk.web.app import create_app

ROOT = Path(__file__).resolve().parents[1]


def _klines(n: int = 80, start: float = 100_000.0, step: float = 40.0) -> list[list]:
    rows: list[list] = []
    t0 = 1_700_000_000_000
    price = start
    for i in range(n):
        open_px = price
        close_px = price + step
        rows.append(
            [
                t0 + i * 3_600_000,
                f"{open_px:.2f}",
                f"{close_px + 15:.2f}",
                f"{open_px - 15:.2f}",
                f"{close_px:.2f}",
                "12.5",
            ]
        )
        price = close_px
    return rows


def _last_close(klines: list[list]) -> float:
    return float(klines[-1][4])


class _FakeResp:
    def __init__(self, payload: object) -> None:
        self._raw = json.dumps(payload).encode("utf-8")
        self.status = 200
        self.code = 200

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *args: object) -> bool:
        return False


class FakeBinance:
    def __init__(self, symbol: str = "BTCUSDT", n: int = 80) -> None:
        self.symbol = symbol
        self.klines = _klines(n)
        self.last = _last_close(self.klines)
        self.calls: list[str] = []

    def __call__(self, request: object, timeout: float | None = None) -> _FakeResp:
        url = getattr(request, "full_url", str(request))
        self.calls.append(url)
        if "ticker/price" in url:
            return _FakeResp({"symbol": self.symbol, "price": f"{self.last:.2f}"})
        if "klines" in url:
            return _FakeResp(self.klines)
        raise urllib.error.URLError(f"unexpected url {url}")


def _client(tmp_path: Path, fake: FakeBinance | None = None) -> TestClient:
    app = create_app(root=ROOT, log_dir=tmp_path)
    if fake is not None:
        app.state.live_urlopen = fake
    return TestClient(app)


def test_normalize_symbol_interval_limit():
    assert normalize_symbol("btc-usdt") == "BTCUSDT"
    assert normalize_interval("1h") == "1h"
    assert normalize_limit(5) == 10
    assert normalize_limit(9999) == 500
    with pytest.raises(ValueError):
        normalize_symbol("..")
    with pytest.raises(ValueError):
        normalize_interval("2d")


def test_fetch_live_market_mocked_parses_price_and_bars():
    fake = FakeBinance()
    market = fetch_live_market("BTCUSDT", interval="1h", limit=80, urlopen=fake)
    assert market.source == SOURCE
    assert market.price.source == SOURCE
    assert market.price.last == fake.last
    assert market.price.symbol == "BTCUSDT"
    assert len(market.bars) == 80
    assert market.bars[-1].close == fake.last
    assert "date,open,high,low,close,volume" in market.bars_csv
    payload = market.to_dict()
    assert payload["mcp_tools"] == ["spot.tickerPrice", "spot.klines"]
    assert "agent.binance.com/mcp/agentic" in payload["mcp_url"]
    assert any("ticker/price" in u for u in fake.calls)
    assert any("klines" in u for u in fake.calls)


def test_klines_roundtrip_csv():
    bars = parse_klines_payload(_klines(12))
    text = bars_to_csv(bars)
    again = load_ohlcv_text(text)
    assert len(again) == 12
    assert again[0].open == bars[0].open
    assert again[-1].close == bars[-1].close


def test_fetch_falls_back_when_primary_is_geo_blocked():
    fake = FakeBinance()
    calls: list[str] = []

    def opener(request: object, timeout: float | None = None) -> _FakeResp:
        url = getattr(request, "full_url", str(request))
        calls.append(url)
        if "api.binance.com" in url:
            raise urllib.error.HTTPError(
                url,
                451,
                "Unavailable For Legal Reasons",
                hdrs=None,  # type: ignore[arg-type]
                fp=io.BytesIO(b"restricted location"),
            )
        return fake(request, timeout=timeout)

    market = fetch_live_market("BTCUSDT", urlopen=opener)
    assert market.price.last == fake.last
    assert "data-api.binance.vision" in market.rest_base
    assert any("api.binance.com" in u for u in calls)
    assert any("data-api.binance.vision" in u for u in calls)


def test_fetch_timeout_is_clear():
    def boom(request: object, timeout: float | None = None) -> None:
        raise TimeoutError("slow")

    with pytest.raises(LiveMarketError, match="Timed out"):
        fetch_live_market(urlopen=boom)


def test_fetch_http_error_is_clear():
    def boom(request: object, timeout: float | None = None) -> None:
        raise urllib.error.HTTPError(
            "https://api.binance.com/api/v3/ticker/price",
            400,
            "Bad Request",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b'{"code":-1121,"msg":"Invalid symbol."}'),
        )

    with pytest.raises(LiveMarketError, match="Invalid symbol"):
        fetch_live_market("BTCUSDT", urlopen=boom)


def test_analyze_live_bars_without_sample_csv(tmp_path: Path):
    desk = Desk(root=ROOT, log_dir=tmp_path)
    bars = parse_klines_payload(_klines(80))
    result = desk.analyze(
        bars=bars,
        use_sample=False,
        symbol="BTCUSDT",
        side="BUY",
        stop=bars[-1].close - 800,
        equity=1000,
        risk_pct=1,
    )
    assert result["source"] == "bars"
    assert result["bars"] == 80
    assert result["setup"]["atr"] is not None
    assert result["suggested_stop"] is not None
    assert result["levels"]["sl"] == result["suggested_stop"]
    assert result["levels"]["tp1"] == result["suggested_tp1"]
    assert result["chart"]["ohlcv"]
    assert result["chart"]["levels"]["sl"] == result["levels"]["sl"]
    assert result["size"]["quantity"] > 0
    assert result["mode"] == "dry-run"


def test_analyze_live_flag_uses_mocked_fetch(tmp_path: Path):
    desk = Desk(root=ROOT, log_dir=tmp_path)
    fake = FakeBinance()
    result = desk.analyze(
        live=True,
        use_sample=False,
        symbol="BTCUSDT",
        side="BUY",
        equity=1000,
        live_urlopen=fake,
    )
    assert result["source"] == "live"
    assert result["badge"] == "LIVE · MCP-shaped"
    assert result["offline"] is False
    assert result["last"] == fake.last
    assert result["live_market"]["source"] == SOURCE
    assert result["live_market"]["mcp_tools"] == ["spot.tickerPrice", "spot.klines"]
    assert result["suggested_stop"] is not None
    assert result["levels"]["sl"] == result["suggested_stop"]
    assert result["chart"]["ohlcv"]
    assert "date,open" in result["bars_csv"]


def test_analyze_sample_path_still_works(tmp_path: Path):
    desk = Desk(root=ROOT, log_dir=tmp_path)
    sample = load_ohlcv(ROOT / "examples" / "btc-ohlcv.csv")
    result = desk.analyze(
        use_sample=True,
        symbol="BTCUSDT",
        side="BUY",
        stop=100200,
        equity=1000,
    )
    assert result["source"] == "sample"
    assert result["bars"] == len(sample)
    assert result["csv_last"] == 102450.0
    assert result["setup"]["signal"] == "BUY"
    assert result["offline"] is True
    assert result["badge"] is None


def test_analyze_requires_some_bars(tmp_path: Path):
    desk = Desk(root=ROOT, log_dir=tmp_path)
    with pytest.raises(ValueError, match="Live from Binance"):
        desk.analyze(use_sample=False, symbol="BTCUSDT")


def test_api_live_and_analyze_live(tmp_path: Path):
    fake = FakeBinance()
    client = _client(tmp_path, fake)
    live = client.get("/api/live?symbol=BTCUSDT&interval=1h&limit=80")
    assert live.status_code == 200
    body = live.json()
    assert body["source"] == SOURCE
    assert body["price"]["last"] == fake.last
    assert len(body["bars"]) == 80
    assert body["mcp_tools"] == ["spot.tickerPrice", "spot.klines"]
    assert "spot.klines" in body["note"]

    analyzed = client.post(
        "/api/analyze",
        json={
            "live": True,
            "use_sample": False,
            "symbol": "BTCUSDT",
            "side": "BUY",
            "equity": 1000,
            "risk_pct": 1,
        },
    )
    assert analyzed.status_code == 200
    data = analyzed.json()
    assert data["source"] == "live"
    assert data["badge"] == "LIVE · MCP-shaped"
    assert data["last"] == fake.last
    assert data["suggested_stop"] is not None
    assert data["levels"]["sl"] == data["suggested_stop"]
    assert data["chart"]["ohlcv"]
    assert data["chart"]["levels"]["atr"] == data["levels"]["atr"]


def test_api_live_bad_symbol(tmp_path: Path):
    client = _client(tmp_path, FakeBinance())
    res = client.get("/api/live?symbol=..")
    assert res.status_code == 400
    assert "symbol" in res.json()["detail"].lower()


def test_api_live_timeout(tmp_path: Path):
    def boom(request: object, timeout: float | None = None) -> None:
        raise TimeoutError("slow")

    app = create_app(root=ROOT, log_dir=tmp_path)
    app.state.live_urlopen = boom
    client = TestClient(app)
    res = client.get("/api/live?symbol=BTCUSDT")
    assert res.status_code == 502
    assert "Timed out" in res.json()["detail"]


def test_ui_exposes_live_from_binance(tmp_path: Path):
    client = _client(tmp_path)
    home = client.get("/")
    assert home.status_code == 200
    assert "Live from Binance" in home.text
    assert "btn-live" in home.text
    assert "Use sample BTC CSV" in home.text
    js = client.get("/static/app.js").text
    assert "Живые данные Binance" in js
    assert "LIVE · MCP-shaped" in js
    assert 'id="btn-live"' in home.text
