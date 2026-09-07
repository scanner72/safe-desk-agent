"""Chart bar times: JS normalizeChartBars → unix seconds for Lightweight Charts.

Live analyze still emits ISO-8601 ``2026-09-06T15:00:00Z`` from the backend.
TradingView Lightweight Charts candlestick ``setData`` needs UTCTimestamp
(unix seconds) for intraday bars — not an ISO string. Conversion lives in
``src/safe_desk/web/static/app.js`` (``normalizeChartTime`` /
``normalizeChartBars``). Backend payload is unchanged.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from safe_desk.desk import Desk
from safe_desk.mcp_input import parse_klines_payload

ROOT = Path(__file__).resolve().parents[1]


def _klines(n: int = 30, start: float = 100_000.0, step: float = 40.0) -> list[list]:
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


APP_JS = ROOT / "src" / "safe_desk" / "web" / "static" / "app.js"
BEGIN = "// CHART_TIME_NORMALIZE_BEGIN"
END = "// CHART_TIME_NORMALIZE_END"


def _extract_normalize_js() -> str:
    text = APP_JS.read_text(encoding="utf-8")
    start = text.index(BEGIN) + len(BEGIN)
    stop = text.index(END)
    body = text[start:stop].strip()
    assert "function normalizeChartTime" in body
    assert "function normalizeChartBars" in body
    return body


def test_app_js_normalizes_and_falls_back_on_setdata_error():
    src = APP_JS.read_text(encoding="utf-8")
    assert "function normalizeChartBars" in src
    assert "function normalizeChartTime" in src
    assert "series.setData(data)" in src
    assert "drawFallbackChart(el, bars, lv)" in src
    lw = src[src.index("function drawLightweightChart") : src.index("function drawFallbackChart")]
    assert "normalizeChartBars(bars)" in lw
    assert "catch (err)" in lw
    fb = src[src.index("function drawFallbackChart") : src.index("function fillRiskBreachDefaults")]
    assert "normalizeChartBars(bars)" in fb
    show = src[src.index("function showChartFromAnalyze") : src.index("function drawChart")]
    assert "ohlcv.length > 0" in show


@pytest.mark.skipif(shutil.which("node") is None, reason="node required to unit-test JS normalize")
def test_normalize_chart_bars_accepts_iso_ms_and_seconds():
    iso = "2026-09-06T15:00:00Z"
    expected_iso = int(datetime(2026, 9, 6, 15, 0, tzinfo=timezone.utc).timestamp())
    expected_day = int(datetime(2026, 6, 17, tzinfo=timezone.utc).timestamp())
    script = f"""
{_extract_normalize_js()}
const cases = {json.dumps({
        "iso": expected_iso,
        "day": expected_day,
    })};
const assert = require("assert");
assert.strictEqual(normalizeChartTime({json.dumps(iso)}), cases.iso);
assert.strictEqual(normalizeChartTime({json.dumps(iso[:-1] + ".000Z")}), cases.iso);
assert.strictEqual(normalizeChartTime("2026-06-17"), cases.day);
assert.strictEqual(normalizeChartTime(cases.iso), cases.iso);
assert.strictEqual(normalizeChartTime(cases.iso * 1000), cases.iso);
assert.strictEqual(normalizeChartTime(String(cases.iso)), cases.iso);
assert.strictEqual(normalizeChartTime(String(cases.iso * 1000)), cases.iso);
assert.strictEqual(normalizeChartTime(""), null);
assert.strictEqual(normalizeChartTime("not-a-time"), null);
const bars = normalizeChartBars([
  {{ time: {json.dumps(iso)}, open: 1, high: 3, low: 0.5, close: 2, volume: 9 }},
  {{ time: "2026-06-17", open: "10", high: "12", low: "9", close: "11" }},
  {{ time: "bad", open: 1, high: 1, low: 1, close: 1 }},
  {{ time: cases.iso, open: 4, high: 5, low: 3, close: 4.5 }},
]);
assert.strictEqual(bars.length, 3);
assert.strictEqual(bars[0].time, cases.iso);
assert.strictEqual(bars[0].close, 2);
assert.strictEqual(bars[1].time, cases.day);
assert.strictEqual(bars[2].time, cases.iso);
console.log("ok");
"""
    proc = subprocess.run(
        ["node", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "ok" in proc.stdout


def test_live_analyze_chart_times_are_iso_js_must_normalize(tmp_path: Path):
    """Document the live payload: ISO strings, not unix seconds.

    JS ``normalizeChartBars`` converts these before Lightweight Charts setData.
    """
    desk = Desk(root=ROOT, log_dir=tmp_path)
    bars = parse_klines_payload(_klines(30))
    result = desk.analyze(
        bars=bars,
        use_sample=False,
        symbol="BTCUSDT",
        side="BUY",
        equity=1000,
        risk_pct=1,
    )
    ohlcv = result["chart"]["ohlcv"]
    assert len(ohlcv) == 30
    first = ohlcv[0]["time"]
    assert isinstance(first, str)
    assert "T" in first and first.endswith("Z")
    parsed = datetime.fromisoformat(first.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None


def test_sample_analyze_still_includes_chart_ohlcv(tmp_path: Path):
    desk = Desk(root=ROOT, log_dir=tmp_path)
    result = desk.analyze(
        use_sample=True,
        symbol="BTCUSDT",
        side="BUY",
        stop=100200,
        equity=1000,
    )
    ohlcv = result["chart"]["ohlcv"]
    assert len(ohlcv) > 0
    assert ohlcv[0]["time"]
    assert ohlcv[0]["close"]

