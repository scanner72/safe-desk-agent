"""Local CLI: analyze CSV bars, size a stop, emit a ticket. No secrets.

Also: merge MCP-shaped price/balance JSON, run the analog proof gate,
and apply desk policy. This helper never calls Binance REST.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from safe_desk.i18n import Lang, norm_lang, t
from safe_desk.indicators import atr, realized_vol, sma_last
from safe_desk.log import append_proposal
from safe_desk.mcp_input import MCP_ENDPOINT, LiveQuote, load_live_quote
from safe_desk.ohlcv import load_ohlcv
from safe_desk.policy import (
    evaluate_policy,
    load_policy,
    resolve_policy_path,
    usage_from_log,
)
from safe_desk.position_sizing import size_spot
from safe_desk.proof import ProofReport, proof_blocks_ticket, run_proof
from safe_desk.risk import evaluate_setup
from safe_desk.ticket import Status, build_ticket


def main(argv: list[str] | None = None) -> int:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--lang", default="en", help="Interface language: en | ru")

    parser = argparse.ArgumentParser(
        prog="safe-desk",
        parents=[shared],
        description=(
            "Safe Desk local helper — indicators, proof, policy, and sizing only. "
            "Trading goes through the official Binance MCP after a human OK."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    analyze = sub.add_parser(
        "analyze",
        parents=[shared],
        help="Score a symbol from an OHLCV CSV (optional MCP-shaped overlays)",
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
    _add_live_flags(analyze)
    analyze.add_argument(
        "--with-proof",
        action="store_true",
        help="Also run the leakage-safe analog proof on this CSV",
    )

    size = sub.add_parser(
        "size",
        parents=[shared],
        help="Size a spot order from equity and stop",
    )
    size.add_argument("--equity", type=float, default=None)
    size.add_argument("--entry", type=float, default=None)
    size.add_argument("--stop", type=float, required=True)
    size.add_argument("--risk-pct", type=float, default=1.0)
    _add_live_flags(size)

    ticket = sub.add_parser(
        "ticket",
        parents=[shared],
        help="Build an awaiting-approval ticket (policy + optional proof gates)",
    )
    ticket.add_argument("--symbol", required=True)
    ticket.add_argument("--side", choices=("BUY", "SELL"), default="BUY")
    ticket.add_argument("--equity", type=float, default=None)
    ticket.add_argument("--entry", type=float, default=None)
    ticket.add_argument("--stop", type=float, required=True)
    ticket.add_argument("--tp", type=float, default=None)
    ticket.add_argument("--risk-pct", type=float, default=1.0)
    ticket.add_argument("--mode", choices=("dry-run", "live"), default="dry-run")
    ticket.add_argument("--rationale", default="")
    ticket.add_argument("--log", type=Path, default=Path("logs/proposals.jsonl"))
    ticket.add_argument("--json", action="store_true")
    _add_live_flags(ticket)
    ticket.add_argument(
        "--proof-csv",
        type=Path,
        default=None,
        help="OHLCV CSV for the analog proof gate",
    )
    ticket.add_argument(
        "--require-proof",
        action="store_true",
        help="REJECT proof → BLOCKED ticket (no AWAITING_APPROVAL)",
    )
    _add_policy_flags(ticket)

    proof = sub.add_parser(
        "proof",
        parents=[shared],
        help="Leakage-safe analog check before proposing a ticket",
    )
    proof.add_argument("csv", type=Path, help="CSV: date,open,high,low,close,volume")
    proof.add_argument("--symbol", default="UNKNOWN")
    proof.add_argument("--side", choices=("BUY", "SELL"), default="BUY")
    proof.add_argument("--window", type=int, default=10)
    proof.add_argument("--horizon", type=int, default=5)
    proof.add_argument("--k", type=int, default=8)
    proof.add_argument("--json", action="store_true")

    policy = sub.add_parser("policy", parents=[shared], help="Desk policy commands")
    policy_sub = policy.add_subparsers(dest="policy_cmd", required=True)
    pcheck = policy_sub.add_parser(
        "check",
        parents=[shared],
        help="Run policy checks (withdrawals always fail)",
    )
    pcheck.add_argument("--symbol", default=None)
    pcheck.add_argument("--side", choices=("BUY", "SELL"), default=None)
    pcheck.add_argument("--notional", type=float, default=None)
    pcheck.add_argument("--risk-pct", type=float, default=None)
    pcheck.add_argument("--product", default="SPOT")
    pcheck.add_argument("--intent", default="ticket", help="ticket | withdraw | transfer_out | …")
    pcheck.add_argument("--daily-loss", type=float, default=None)
    pcheck.add_argument("--daily-volume", type=float, default=None)
    pcheck.add_argument("--log", type=Path, default=None, help="Optional proposals.jsonl for daily caps")
    pcheck.add_argument("--json", action="store_true")
    _add_policy_flags(pcheck)

    quote = sub.add_parser(
        "quote",
        parents=[shared],
        help="Format MCP-shaped price/balance JSON for sizing (no network)",
    )
    _add_live_flags(quote, required_any=True)
    quote.add_argument("--symbol", default=None)
    quote.add_argument("--json", action="store_true")

    serve = sub.add_parser(
        "serve",
        parents=[shared],
        help="Local dry-run desk UI (stdlib HTTP, no secrets)",
    )
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)

    args = parser.parse_args(argv)
    lang = norm_lang(args.lang)
    if args.cmd == "analyze":
        return _cmd_analyze(args, lang)
    if args.cmd == "size":
        return _cmd_size(args, lang)
    if args.cmd == "ticket":
        return _cmd_ticket(args, lang)
    if args.cmd == "proof":
        return _cmd_proof(args, lang)
    if args.cmd == "policy":
        return _cmd_policy_check(args, lang)
    if args.cmd == "quote":
        return _cmd_quote(args, lang)
    if args.cmd == "serve":
        from safe_desk.web import serve as serve_ui

        serve_ui(host=args.host, port=args.port)
        return 0
    parser.error(f"unknown command {args.cmd}")
    return 2


def _add_live_flags(parser: argparse.ArgumentParser, *, required_any: bool = False) -> None:
    parser.add_argument(
        "--price-json",
        type=Path,
        default=None,
        help="MCP-shaped ticker JSON (pasted/fetched by the LLM). No secrets.",
    )
    parser.add_argument(
        "--balance-json",
        type=Path,
        default=None,
        help="MCP-shaped Agentic balance JSON. No secrets.",
    )
    parser.add_argument(
        "--quote-asset",
        default="USDT",
        help="Quote asset to read from balance JSON (default USDT)",
    )
    if required_any:
        # validated in the command
        pass


def _add_policy_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="Policy YAML/JSON (default: config/policy.yaml or policy.example.*)",
    )
    parser.add_argument(
        "--no-policy",
        action="store_true",
        help="Skip the policy file; still apply hard refuses (withdraw / 1% max)",
    )


def _cmd_analyze(args: argparse.Namespace, lang: Lang) -> int:
    bars = load_ohlcv(args.csv)
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    csv_last = closes[-1]
    live = _optional_live(args)
    last = csv_last if live is None or live.last is None else live.last
    equity = args.equity
    if equity is None and live is not None:
        equity = live.equity

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
    if live is not None and live.last is not None and abs(live.last - csv_last) > 1e-9:
        print(f"{'CSV last':<14}{_fmt(csv_last)}")
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
    if live is not None:
        for note in live.notes:
            print(f"  - {note}")
    if equity and args.stop:
        sized = size_spot(equity, last, args.stop, args.risk_pct, lang=lang)
        print()
        print(t(lang, "illustrative_size"))
        print(
            f"  qty {_qty(sized.quantity)}   notional {_fmt(sized.notional)}   "
            f"risk {_fmt(sized.risk_quote)}"
        )
        for note in sized.notes:
            print(f"  - {note}")
    if args.with_proof:
        proof = run_proof(bars, symbol=args.symbol, side=args.side)
        print()
        _print_proof(proof, lang)
    print()
    print(t(lang, "no_mcp"))
    return 0


def _cmd_size(args: argparse.Namespace, lang: Lang) -> int:
    live = _optional_live(args)
    equity = args.equity if args.equity is not None else (None if live is None else live.equity)
    entry = args.entry if args.entry is not None else (None if live is None else live.last)
    if equity is None or entry is None:
        print("size needs --equity and --entry, or MCP-shaped --price-json / --balance-json", file=sys.stderr)
        return 2
    sized = size_spot(equity, entry, args.stop, args.risk_pct, lang=lang)
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
    notes = list(sized.notes)
    if live is not None:
        notes.extend(live.notes)
    if notes:
        print()
        print(t(lang, "notes"))
        for note in notes:
            print(f"  - {note}")
    return 0


def _cmd_ticket(args: argparse.Namespace, lang: Lang) -> int:
    live = _optional_live(args)
    equity = args.equity if args.equity is not None else (None if live is None else live.equity)
    entry = args.entry if args.entry is not None else (None if live is None else live.last)
    if equity is None or entry is None:
        print(
            "ticket needs --equity and --entry, or MCP-shaped --price-json / --balance-json",
            file=sys.stderr,
        )
        return 2

    extra_notes: list[str] = []
    if live is not None:
        extra_notes.extend(live.notes)

    sized = size_spot(equity, entry, args.stop, args.risk_pct, lang=lang)

    cfg = None
    if not args.no_policy:
        policy_path = resolve_policy_path(
            args.policy,
            env_path=os.environ.get("SAFE_DESK_POLICY"),
        )
        if policy_path is not None:
            cfg = load_policy(policy_path)
    daily_loss, daily_volume = usage_from_log(args.log)
    policy = evaluate_policy(
        intent="ticket",
        symbol=args.symbol,
        side=args.side,
        notional=sized.notional,
        risk_pct=args.risk_pct,
        product="SPOT",
        daily_loss=daily_loss,
        daily_volume=daily_volume,
        config=cfg,
    )

    proof: ProofReport | None = None
    if args.proof_csv is not None:
        proof = run_proof(load_ohlcv(args.proof_csv), symbol=args.symbol, side=args.side)
        extra_notes.append(
            f"Proof {proof.verdict} receipt={proof.receipt_hash}: {proof.rationale}"
        )

    status: Status = "awaiting_approval"
    blocked_reasons: list[str] = []
    if not policy.ok:
        status = "blocked"
        for v in policy.violations:
            blocked_reasons.append(f"Policy {v.code}: {v.message}")
            extra_notes.append(f"Policy {v.code}: {v.message}")
    proof_blocked, proof_note = proof_blocks_ticket(
        proof,
        mode=args.mode,
        require_proof=args.require_proof,
    )
    if proof_note:
        extra_notes.append(proof_note)
    if proof_blocked:
        status = "blocked"
        blocked_reasons.append(proof_note or "proof gate")

    ticket = build_ticket(
        symbol=args.symbol,
        side=args.side,
        entry=entry,
        stop=args.stop,
        equity=equity,
        take_profit=args.tp,
        risk_pct=args.risk_pct,
        mode=args.mode,
        rationale=args.rationale,
        when=datetime.now(timezone.utc),
        lang=lang,
        extra_notes=extra_notes,
        size=sized,
        status=status,
        proof=None if proof is None else proof.summary_dict(),
        policy=policy.to_dict(),
    )
    action = "blocked" if status == "blocked" else "proposed"
    log_path = append_proposal(ticket, action=action, path=args.log)
    if args.json:
        print(ticket.to_json())
    else:
        print(ticket.render())
        print(t(lang, "logged", ticket_id=ticket.id, path=log_path))
        if status == "blocked":
            print(t(lang, "policy_fail"))
            for reason in blocked_reasons:
                print(f"  - {reason}")
    return 2 if status == "blocked" else 0


def _cmd_proof(args: argparse.Namespace, lang: Lang) -> int:
    bars = load_ohlcv(args.csv)
    report = run_proof(
        bars,
        symbol=args.symbol,
        side=args.side,
        window=args.window,
        horizon=args.horizon,
        k=args.k,
    )
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=False))
    else:
        _print_proof(report, lang)
    if report.verdict == "REJECT":
        return 2
    return 0


def _cmd_policy_check(args: argparse.Namespace, lang: Lang) -> int:
    cfg = None
    if not args.no_policy:
        policy_path = resolve_policy_path(
            args.policy,
            env_path=os.environ.get("SAFE_DESK_POLICY"),
        )
        if policy_path is not None:
            cfg = load_policy(policy_path)
    daily_loss = args.daily_loss
    daily_volume = args.daily_volume
    if daily_loss is None or daily_volume is None:
        scanned_loss, scanned_vol = usage_from_log(args.log)
        if daily_loss is None:
            daily_loss = scanned_loss
        if daily_volume is None:
            daily_volume = scanned_vol
    result = evaluate_policy(
        intent=args.intent,
        symbol=args.symbol,
        side=args.side,
        notional=args.notional,
        risk_pct=args.risk_pct,
        product=args.product,
        daily_loss=daily_loss,
        daily_volume=daily_volume,
        config=cfg,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(t(lang, "policy_header", intent=result.intent))
        print("\u2500" * 48)
        print(f"{'Result':<16}{'PASS' if result.ok else 'FAIL'}")
        print(f"{'Config':<16}{result.config_source}")
        print(f"{'Emergency':<16}{result.emergency_stop}")
        if args.symbol:
            print(f"{'Symbol':<16}{args.symbol.upper()}")
        if args.notional is not None:
            print(f"{'Notional':<16}{_fmt(args.notional)}")
        if args.risk_pct is not None:
            print(f"{'Risk %':<16}{args.risk_pct:g}")
        if result.violations:
            print()
            print("Violations")
            for v in result.violations:
                print(f"  - {v.code}: {v.message}")
        print()
        print(t(lang, "policy_pass") if result.ok else t(lang, "policy_fail"))
        print(f"Withdrawals and transfer-out are always refused. MCP: {MCP_ENDPOINT}")
    return 0 if result.ok else 2


def _cmd_quote(args: argparse.Namespace, lang: Lang) -> int:
    if args.price_json is None and args.balance_json is None:
        print("quote needs --price-json and/or --balance-json", file=sys.stderr)
        return 2
    live = load_live_quote(
        price_source=args.price_json,
        balance_source=args.balance_json,
        symbol=args.symbol,
        quote_asset=args.quote_asset,
    )
    if args.json:
        print(json.dumps(live.to_dict(), indent=2))
        return 0
    print(t(lang, "live_path"))
    print("\u2500" * 48)
    print(f"{'MCP endpoint':<16}{MCP_ENDPOINT}")
    print(f"{'Symbol':<16}{live.symbol or '—'}")
    print(f"{'Last':<16}{_fmt(live.last)}")
    print(f"{'Equity':<16}{_fmt(live.equity)}  {live.quote_asset} (Agentic free)")
    print()
    print("Pass these numbers into `safe_desk size` / `ticket`, or into the SYSTEM ticket flow.")
    print("This helper did not call Binance REST and holds no API keys.")
    for note in live.notes:
        print(f"  - {note}")
    return 0


def _optional_live(args: argparse.Namespace) -> LiveQuote | None:
    price = getattr(args, "price_json", None)
    balance = getattr(args, "balance_json", None)
    if price is None and balance is None:
        return None
    return load_live_quote(
        price_source=price,
        balance_source=balance,
        symbol=getattr(args, "symbol", None),
        quote_asset=getattr(args, "quote_asset", "USDT"),
    )


def _print_proof(report: ProofReport, lang: Lang) -> None:
    print(t(lang, "proof_header", symbol=report.symbol))
    print("\u2500" * 48)
    print(f"{'Verdict':<16}{report.verdict}")
    print(f"{'Side':<16}{report.side}")
    print(f"{'Analogs':<16}{report.n_analogs}  (k={report.k}, window={report.window}, horizon={report.horizon})")
    med = "—" if report.median_forward_return is None else f"{report.median_forward_return:+.2%}"
    hit = "—" if report.hit_rate is None else f"{report.hit_rate:.0%}"
    print(f"{'Median fwd':<16}{med}")
    print(f"{'Hit rate':<16}{hit}")
    print(f"{'Receipt':<16}{report.receipt_hash}")
    print(f"{'Leakage-safe':<16}{report.leakage_safe}")
    print()
    print(report.rationale)
    if report.analogs:
        print()
        print("Nearest analogs (end date, distance, forward return, hit)")
        for match in report.analogs[:5]:
            print(
                f"  - {match.end_date or match.end_index}  d={match.distance:.3f}  "
                f"fwd={match.forward_return:+.2%}  hit={match.hit}"
            )


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
