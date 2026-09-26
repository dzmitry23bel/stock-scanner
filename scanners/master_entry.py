"""Shared ranking helpers for combining independent scanner evidence.

The master score is deliberately a *setup* score, not a prediction. It rewards
agreement between trend, pullback/reversal confirmation, and tradeability while
penalizing weak risk/reward and unconfirmed reversals.
"""
from __future__ import annotations

from math import isfinite
from typing import Any


ACTIONABLE = {
    "🟢 STRONG KNIFE CATCH",
    "🟢 LONG CANDIDATE",
    "BUY DIP",
    "MOMENTUM BUY",
    "LONG",
    "SHORT",
}


def _clip(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _num(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return value if isfinite(value) else default


def signal_strength(signal: dict[str, Any]) -> float:
    """Normalize a scanner's native score to 0..100."""
    return _clip(_num(signal.get("score")))


def risk_reward(signal: dict[str, Any]) -> float:
    entry = _num(signal.get("entry"), float("nan"))
    stop = _num(signal.get("stop"), float("nan"))
    tp2 = _num(signal.get("tp2"), float("nan"))
    if entry != entry or stop != stop or tp2 != tp2 or entry == stop:
        return 0.0
    risk = abs(entry - stop)
    reward = abs(tp2 - entry)
    return reward / risk if risk else 0.0


def analyst_target_score(target: dict[str, Any] | None) -> float:
    """Convert median-target upside into a bounded 0..100 enrichment score.

    Missing/invalid targets are neutral (50), so analyst data cannot manufacture
    a signal.
    """
    if not target or not target.get("target_available"):
        return 50.0
    upside = _num(target.get("upside_pct"), 0.0)
    return _clip(50.0 + upside * 1.5)


def build_master_scores(
    signals_by_scanner: dict[str, list[dict[str, Any]]],
    analyst_targets: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Combine scanner evidence into one score per ticker.

    Weights:
      - business quality: 25%
      - EMA / entry timing: 25%
      - trend/momentum: 20%
      - reversal / pullback confirmation: 10%
      - cross-scanner agreement: 10%
      - risk/reward quality: 5%
      - analyst target enrichment: 5%

    WAIT/WATCH results still contribute evidence but cannot become an entry on
    score alone. A trade requires at least one actionable scanner and R:R >= 1.5.
    """
    by_ticker: dict[str, dict[str, dict[str, Any]]] = {}

    for scanner, rows in signals_by_scanner.items():
        for row in rows:
            ticker = str(row.get("ticker", "")).upper().strip()
            if ticker:
                by_ticker.setdefault(ticker, {})[scanner] = row

    result: list[dict[str, Any]] = []
    for ticker, evidence in by_ticker.items():
        tm = evidence.get("trend_momentum", {})
        kc = evidence.get("knife_catch", {})
        dt = evidence.get("day_trade", {})

        tm_score = signal_strength(tm)
        kc_score = signal_strength(kc)
        dt_score = signal_strength(dt)
        quality_score = _clip(_num(tm.get("quality_score"), 50.0))
        ema_timing_score = _clip(_num(tm.get("ema_timing_score"), 50.0))
        target = (analyst_targets or {}).get(ticker)
        analyst_score = analyst_target_score(target)

        tm_active = tm.get("signal") in {"BUY DIP", "MOMENTUM BUY"}
        kc_active = kc.get("signal") in {"🟢 STRONG KNIFE CATCH", "🟢 LONG CANDIDATE"}
        dt_active = dt.get("signal") in {"LONG", "SHORT"}

        actionable_count = sum((tm_active, kc_active, dt_active))
        agreement = 100.0 * actionable_count / 3.0

        rr_values = [risk_reward(row) for row in (tm, kc, dt)]
        rr_best = max(rr_values, default=0.0)
        rr_component = _clip((rr_best - 1.0) / 2.0 * 100.0)

        # Evidence from the specialist scanners.
        trend_component = tm_score
        reversal_component = max(kc_score, 0.6 * tm_score)
        confirmation_component = dt_score

        # A strong company at a bad price should not outrank a strong company
        # that is actually in a sensible EMA pullback zone.
        master = (
            0.25 * quality_score
            + 0.25 * ema_timing_score
            + 0.20 * trend_component
            + 0.10 * reversal_component
            + 0.10 * agreement
            + 0.05 * rr_component
            + 0.05 * analyst_score
        )

        # Hard gating: do not turn a high-quality stock into an entry without
        # confirmation. The output remains useful as SETUP/WAIT.
        status = "WATCH"
        if actionable_count and rr_best >= 1.5:
            status = "ENTRY" if actionable_count >= 2 or kc_active or dt_active else "SETUP"
        elif tm_active or kc_active or dt_active:
            status = "SETUP"

        # Avoid false precision: an entry status with no actual trade levels is
        # downgraded to SETUP.
        representative = next(
            (row for row in (dt, kc, tm) if row.get("entry") is not None),
            {},
        )
        if status == "ENTRY" and not all(
            representative.get(key) is not None for key in ("entry", "stop", "tp1", "tp2")
        ):
            status = "SETUP"

        result.append(
            {
                "ticker": ticker,
                "master_score": round(_clip(master), 1),
                "status": status,
                "trend_score": round(tm_score, 1),
                "quality_score": round(quality_score, 1),
                "ema_timing_score": round(ema_timing_score, 1),
                "ema_zone": tm.get("ema_zone"),
                "vs_ema20": tm.get("vs_ema20"),
                "vs_ema50": tm.get("vs_ema50"),
                "knife_score": round(kc_score, 1),
                "day_score": round(dt_score, 1),
                "agreement": round(agreement, 1),
                "rr": round(rr_best, 2),
                "analyst_target": target.get("target") if target else None,
                "analyst_mean": target.get("mean") if target else None,
                "analyst_low": target.get("low") if target else None,
                "analyst_high": target.get("high") if target else None,
                "analyst_upside_pct": target.get("upside_pct") if target else None,
                "analyst_score": round(analyst_score, 1),
                "entry": representative.get("entry"),
                "stop": representative.get("stop"),
                "tp1": representative.get("tp1"),
                "tp2": representative.get("tp2"),
                "signals": {
                    scanner: row.get("signal") for scanner, row in evidence.items()
                },
            }
        )

    return sorted(result, key=lambda row: row["master_score"], reverse=True)
