"""Local CLI: analyze CSV bars, size a stop, emit a ticket. No secrets."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from safe_desk.i18n import Lang, norm_lang, t
from safe_desk.indicators import atr, realized_vol, sma_last
from safe_desk.log import append_proposal
from safe_desk.ohlcv import load_ohlcv
from safe_desk.position_sizing import size_spot
from safe_desk.risk import evaluate_setup
from safe_desk.ticket import build_ticket


def main(argv: list[str] | None = None) -> int:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--lang", default="en", help="Interface language: en | ru")

    parser = argparse.ArgumentParser(
        prog="safe-desk",
        parents=[shared],
        description=(
            "Safe Desk local helper — indicators and sizing only. "
            "Trading goes through the official Binance MCP after a human OK."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    analyze = sub.add_parser(
        "analyze",
        parents=[shared],
        help="Score a symbol from an OHLCV CSV",
    )
    analyze.add_argument("csv", type=Path, help="CSV: date,open,high,low,close,volume")
    analyze.add_argument("--symbol", default="UNKNOWN")
    analyze.add_argument("--side", choices=("BUY", "SELL"), default="BUY")
    analyze.add_argument("--fast", type=int, default=20)
    analyze.add_argument("--slow", type=int, default=50)
    analyze.add_argument("--atr-period", type=int, default=14)
    analyze.add_argument("--stop", type=float, default=None)
    analyze.add_argument("--equity", type=float, default=None)
    analyze.add_argument("--risk-pct", type=float, default=1.0)

    size = sub.add_parser(
        "size",
        parents=[shared],
        help="Size a spot order from equity and stop",
    )
    size.add_argument("--equity", type=float, required=True)
    size.add_argument("--entry", type=float, required=True)
    size.add_argument("--stop", type=float, required=True)
    size.add_argument("--risk-pct", type=float, default=1.0)

    ticket = sub.add_parser(
        "ticket",
        parents=[shared],
        help="Build an awaiting-approval ticket and log it",
    )
    ticket.add_argument("--symbol", required=True)
    ticket.add_argument("--side", choices=("BUY", "SELL"), default="BUY")
    ticket.add_argument("--equity", type=float, required=True)
    ticket.add_argument("--entry", type=float, required=True)
    ticket.add_argument("--stop", type=float, required=True)
    ticket.add_argument("--tp", type=float, default=None)
    ticket.add_argument("--risk-pct", type=float, default=1.0)
    ticket.add_argument("--mode", choices=("dry-run", "live"), default="dry-run")
    ticket.add_argument("--rationale", default="")
    ticket.add_argument("--log", type=Path, default=Path("logs/proposals.jsonl"))
    ticket.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    lang = norm_lang(args.lang)
    if args.cmd == "analyze":
        return _cmd_analyze(args, lang)
    if args.cmd == "size":
        return _cmd_size(args, lang)
    if args.cmd == "ticket":
        return _cmd_ticket(args, lang)
    parser.error(f"unknown command {args.cmd}")
    return 2


def _cmd_analyze(args: argparse.Namespace, lang: Lang) -> int:
    bars = load_ohlcv(args.csv)
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    last = closes[-1]
    fast = sma_last(closes, args.fast)
    slow = sma_last(closes, args.slow)
    atr_value = atr(highs, lows, closes, args.atr_period)
    vol = realized_vol(closes, period=min(20, max(2, len(closes) - 1)))
    report = evaluate_setup(
        last=last,
        sma_fast=fast,
        sma_slow=slow,
        atr_value=atr_value,
        realized_vol_value=vol,
        side=args.side,
        stop=args.stop,
        lang=lang,
    )
    print(t(lang, "analyze_header", symbol=args.symbol.upper()))
    print("\u2500" * 48)
    print(f"{t(lang, 'bars'):<14}{len(bars)}")
    print(f"{t(lang, 'last'):<14}{_fmt(last)}")
    print(f"{'SMA' + str(args.fast):<14}{_fmt(fast)}")
    print(f"{'SMA' + str(args.slow):<14}{_fmt(slow)}")
    atr_txt = _fmt(atr_value)
    if report.atr_pct is not None:
        atr_txt += f"  ({report.atr_pct:.2f}%)"
    print(f"{'ATR(' + str(args.atr_period) + ')':<14}{atr_txt}")
    rvol = "\u2014" if report.realized_vol is None else f"{100 * report.realized_vol:.1f}% {t(lang, 'ann')}"
    print(f"{t(lang, 'realized_vol'):<14}{rvol}")
    print(f"{t(lang, 'trend'):<14}{report.trend}")
    print(f"{t(lang, 'vol_regime'):<14}{report.vol_regime}")
    print(f"{t(lang, 'risk_score'):<14}{report.risk_score} / 100")
    print(f"{t(lang, 'signal'):<14}{report.signal}  {t(lang, 'signal_note')}")
    print()
    print(t(lang, "reasons"))
    for reason in report.reasons:
        print(f"  - {reason}")
    if args.equity and args.stop:
        sized = size_spot(args.equity, last, args.stop, args.risk_pct, lang=lang)
        print()
        print(t(lang, "illustrative_size"))
        print(
            f"  qty {_qty(sized.quantity)}   notional {_fmt(sized.notional)}   "
            f"risk {_fmt(sized.risk_quote)}"
        )
        for note in sized.notes:
            print(f"  - {note}")
    print()
    print(t(lang, "no_mcp"))
    return 0


def _cmd_size(args: argparse.Namespace, lang: Lang) -> int:
    sized = size_spot(args.equity, args.entry, args.stop, args.risk_pct, lang=lang)
    print(t(lang, "size_header"))
    print("\u2500" * 48)
    print(f"{t(lang, 'equity'):<16}{_fmt(sized.equity)}")
    print(f"{t(lang, 'entry'):<16}{_fmt(sized.entry)}")
    print(f"{t(lang, 'stop'):<16}{_fmt(sized.stop)}")
    print(f"{t(lang, 'stop_distance'):<16}{_fmt(sized.stop_distance)}  ({sized.stop_pct:.2f}%)")
    print(f"{t(lang, 'risk_pct'):<16}{sized.risk_pct:g}%")
    print(f"{t(lang, 'risk_quote'):<16}{_fmt(sized.risk_quote)}")
    print(f"{t(lang, 'quantity'):<16}{_qty(sized.quantity)}")
    print(f"{t(lang, 'notional'):<16}{_fmt(sized.notional)}")
    if sized.notes:
        print()
        print(t(lang, "notes"))
        for note in sized.notes:
            print(f"  - {note}")
    return 0


def _cmd_ticket(args: argparse.Namespace, lang: Lang) -> int:
    ticket = build_ticket(
        symbol=args.symbol,
        side=args.side,
        entry=args.entry,
        stop=args.stop,
        equity=args.equity,
        take_profit=args.tp,
        risk_pct=args.risk_pct,
        mode=args.mode,
        rationale=args.rationale,
        when=datetime.now(timezone.utc),
        lang=lang,
    )
    log_path = append_proposal(ticket, action="proposed", path=args.log)
    if args.json:
        print(ticket.to_json())
    else:
        print(ticket.render())
        print(t(lang, "logged", ticket_id=ticket.id, path=log_path))
    return 0


def _fmt(value: float | None) -> str:
    if value is None:
        return "\u2014"
    if abs(value) >= 1000:
        return f"{value:,.2f}"
    if abs(value) >= 1:
        return f"{value:,.4f}"
    return f"{value:.8f}".rstrip("0").rstrip(".")


def _qty(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")


if __name__ == "__main__":
    sys.exit(main())
