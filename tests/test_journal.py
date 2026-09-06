from pathlib import Path

import pytest

from safe_desk.journal import (
    PAPER_LABEL,
    append_paper_entry,
    append_paper_exit,
    open_positions,
    running_pnl,
    summarize,
)


def test_paper_entry_and_exit_running_pnl(tmp_path: Path):
    path = tmp_path / "paper_journal.jsonl"
    entry = append_paper_entry(
        ticket_id="TKT-20260906-120000",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.00444444,
        price=102450,
        path=path,
    )
    assert entry.label == PAPER_LABEL
    assert entry.simulated is True
    assert "SIMULATED" in entry.note
    assert "live" in entry.note.lower()
    assert entry.pnl is None
    assert running_pnl(path) == 0.0
    assert len(open_positions(path)) == 1

    exit_ev = append_paper_exit(
        ticket_id="TKT-20260906-120000",
        exit_price=106950,
        reason="take_profit",
        path=path,
    )
    expected = (106950 - 102450) * 0.00444444
    assert exit_ev.pnl == pytest.approx(expected)
    assert exit_ev.running_pnl == pytest.approx(expected)
    assert running_pnl(path) == pytest.approx(expected)
    assert open_positions(path) == []

    summary = summarize(path)
    assert summary["simulated"] is True
    assert "not live" in summary["note"].lower()
    assert summary["closed_count"] == 1
    assert summary["label"] == PAPER_LABEL


def test_sell_paper_pnl_and_missing_open(tmp_path: Path):
    path = tmp_path / "paper_journal.jsonl"
    append_paper_entry(
        ticket_id="TKT-20260906-130000",
        symbol="ETHUSDT",
        side="SELL",
        quantity=1.0,
        price=4000,
        path=path,
    )
    exit_ev = append_paper_exit(
        ticket_id="TKT-20260906-130000",
        exit_price=3900,
        reason="stop",
        path=path,
    )
    assert exit_ev.pnl == pytest.approx(100.0)
    with pytest.raises(ValueError, match="no open PAPER"):
        append_paper_exit(ticket_id="TKT-20260906-130000", exit_price=3800, path=path)
