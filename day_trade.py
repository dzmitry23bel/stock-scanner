#!/usr/bin/env python3
"""Day Trading Score scanner (1-5 day horizon, leveraged setups).

Separate from the long-term score in scanner.py. Computes a 0-100 Day Score
(Momentum 25% / Trend 20% / Entry 20% / Volume 15% / Catalyst 10% / Risk 10%),
classifies each ticker LONG / SHORT / WAIT, and prints a trade plan (entry
zone, stop, TP1/TP2, R:R) for the top setups sized off ATR.

VWAP / opening-range / RVOL are approximated from yfinance 5-minute bars for
the most recent session (Yahoo Finance intraday history is limited to the
last ~60 days) -- these are best-effort estimates, not a real-time feed.
Always confirm live price/VWAP/volume before entering a leveraged trade.

Usage:
    python day_trade.py                              # scan tickers.txt
    python day_trade.py MRVL AAPL CRDO
    python day_trade.py --catalysts catalysts.json --top 20 --leverage 5
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional

import pandas as pd
import yfinance as yf

from scanner import load_catalysts, load_tickers

try:
    from rich.console import Console
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

DIRECTION_EMOJI = {"LONG": "🟢", "SHORT": "🔴", "WAIT": "🟡"}


def fetch_daily(ticker: str) -> Optional[pd.DataFrame]:
    try:
        df = yf.Ticker(ticker).history(period="1y", auto_adjust=True)
    except Exception:
        return None
    return df if df is not None and not df.empty and len(df) >= 60 else None


def fetch_intraday(ticker: str) -> Optional[pd.DataFrame]:
    try:
        df = yf.Ticker(ticker).history(period="5d", interval="5m", auto_adjust=False)
    except Exception:
        return None
    return df if df is not None and not df.empty else None


def compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return float(true_range.rolling(period).mean().iloc[-1])


def session_metrics(intraday: pd.DataFrame) -> dict:
    """VWAP, opening-range high/low, gap % and RVOL for the latest session."""
    last_day = intraday.index[-1].date()
    session = intraday[intraday.index.date == last_day]
    other_days = intraday[intraday.index.date != last_day]

    typical = (session["High"] + session["Low"] + session["Close"]) / 3
    vol_sum = float(session["Volume"].sum())
    vwap = float((typical * session["Volume"]).sum() / vol_sum) if vol_sum else float("nan")

    opening = session.iloc[: min(6, len(session))]  # ~30 min of 5-minute bars
    orb_high = float(opening["High"].max())
    orb_low = float(opening["Low"].min())

    if not other_days.empty:
        by_day_volume = other_days.groupby(other_days.index.date)["Volume"].sum()
        avg_day_volume = float(by_day_volume.mean()) if len(by_day_volume) else float("nan")
        prev_close = float(other_days["Close"].iloc[-1])
        gap_pct = float((session["Open"].iloc[0] / prev_close - 1) * 100)
    else:
        avg_day_volume = float("nan")
        gap_pct = float("nan")

    rvol = vol_sum / avg_day_volume if avg_day_volume == avg_day_volume and avg_day_volume else float("nan")

    return {
        "vwap": vwap,
        "orb_high": orb_high,
        "orb_low": orb_low,
        "rvol": rvol,
        "gap_pct": gap_pct,
    }


def analyze_day(ticker: str, catalyst_days: Optional[int]) -> Optional[dict]:
    daily = fetch_daily(ticker)
    if daily is None:
        return None

    close = daily["Close"]
    price = float(close.iloc[-1])
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()
    ma20_now, ma50_now = float(ma20.iloc[-1]), float(ma50.iloc[-1])
    ma200_now = float(ma200.iloc[-1]) if len(close) >= 200 else float("nan")

    ret_1d = float((close.iloc[-1] / close.iloc[-2] - 1) * 100) if len(close) > 1 else float("nan")
    ret_1w = float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) > 6 else float("nan")
    ret_1m = float((close.iloc[-1] / close.iloc[-22] - 1) * 100) if len(close) > 22 else float("nan")

    atr = compute_atr(daily)
    atr_pct = atr / price * 100 if price else float("nan")
    dist_from_ma20 = (price / ma20_now - 1) * 100 if ma20_now == ma20_now else float("nan")

    intraday = fetch_intraday(ticker)
    session = session_metrics(intraday) if intraday is not None else None
    rvol = session["rvol"] if session else float("nan")
    vwap = session["vwap"] if session else float("nan")
    gap_pct = session["gap_pct"] if session else float("nan")
    orb_high = session["orb_high"] if session else float("nan")
    orb_low = session["orb_low"] if session else float("nan")

    # --- Momentum (25) ---
    momentum = 0.0
    momentum += 10 if ret_1d == ret_1d and ret_1d > 0 else 0
    momentum += 8 if ret_1w == ret_1w and ret_1w > 0 else 0
    momentum += 7 if ret_1m == ret_1m and ret_1m > 0 else 0

    # --- Trend (20) ---
    trend = 0.0
    trend += 8 if price > ma20_now else 0
    trend += 7 if ma50_now == ma50_now and ma20_now > ma50_now else 0
    trend += 5 if ma200_now == ma200_now and price > ma200_now else 0

    # --- Entry (20): near a valid entry, not already extended ---
    entry = 0.0
    if dist_from_ma20 == dist_from_ma20:
        if abs(dist_from_ma20) <= 3:
            entry += 12
        elif abs(dist_from_ma20) <= 6:
            entry += 6
        if ret_1w == ret_1w and ret_1m == ret_1m and ret_1w < 0 <= ret_1m:
            entry += 8  # pullback within an uptrend

    # --- Volume (15) ---
    volume = 0.0
    if rvol == rvol:
        volume = 15 if rvol > 2 else 12 if rvol > 1.5 else 7 if rvol > 1 else 0

    # --- Catalyst (10) ---
    catalyst = 0.0
    if catalyst_days is not None:
        catalyst = 10 if catalyst_days <= 3 else 7 if catalyst_days <= 7 else 3 if catalyst_days <= 30 else 0

    # --- Risk (10): penalize gap/volatility extremes ---
    risk = 10.0
    if atr_pct == atr_pct and atr_pct > 8:
        risk -= 5
    if gap_pct == gap_pct and abs(gap_pct) > 7:
        risk -= 5
    risk = max(0.0, risk)

    day_score = max(0, min(100, round(momentum + trend + entry + volume + catalyst + risk)))

    overextended = abs(dist_from_ma20) > 8 if dist_from_ma20 == dist_from_ma20 else False
    volume_ok = rvol != rvol or rvol > 1  # unknown RVOL doesn't block, but a low one does
    long_ok = (
        price > ma20_now
        and ma50_now == ma50_now
        and ma20_now > ma50_now
        and ret_1d == ret_1d
        and ret_1d > 0
        and volume_ok
        and not overextended
    )
    short_ok = (
        price < ma20_now
        and ma50_now == ma50_now
        and ma20_now < ma50_now
        and ret_1d == ret_1d
        and ret_1d < 0
        and volume_ok
    )
    direction = "LONG" if long_ok else "SHORT" if short_ok else "WAIT"

    return {
        "ticker": ticker,
        "price": price,
        "ma20": ma20_now,
        "atr": atr,
        "atr_pct": atr_pct,
        "vwap": vwap,
        "orb_high": orb_high,
        "orb_low": orb_low,
        "rvol": rvol,
        "gap_pct": gap_pct,
        "dist_from_ma20": dist_from_ma20,
        "day_score": day_score,
        "direction": direction,
        "overextended": overextended,
    }


def fmt(value: float, suffix: str = "") -> str:
    return "n/a" if value != value else f"{value:+.2f}{suffix}"


def build_trade_plan(row: dict) -> Optional[dict]:
    price, atr = row["price"], row["atr"]
    if atr != atr or atr <= 0 or row["direction"] == "WAIT":
        return None

    if row["direction"] == "LONG":
        entry_low, entry_high = price - 0.3 * atr, price + 0.1 * atr
        stop = entry_low - 1.0 * atr
        tp1 = entry_high + 1.0 * atr
        tp2 = entry_high + 2.4 * atr
        risk = entry_high - stop
        reward = tp2 - entry_high
    else:
        entry_low, entry_high = price - 0.1 * atr, price + 0.3 * atr
        stop = entry_high + 1.0 * atr
        tp1 = entry_low - 1.0 * atr
        tp2 = entry_low - 2.4 * atr
        risk = stop - entry_low
        reward = entry_low - tp2

    rr = reward / risk if risk > 0 else float("nan")
    return {
        "entry_low": entry_low,
        "entry_high": entry_high,
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2,
        "rr": rr,
    }


def print_trade_plans(rows_with_plans: list[tuple[dict, dict]]) -> None:
    if not rows_with_plans:
        return

    if HAS_RICH:
        console = Console(width=140)
        table = Table(title="Trade Plans")
        for col in ("Symbol", "Dir", "Score", "Entry", "Stop", "TP1", "TP2", "R:R", "Setup", "Status"):
            table.add_column(col, justify="right" if col in ("Score", "Entry", "Stop", "TP1", "TP2", "R:R") else "left")
        for row, plan in rows_with_plans:
            setup = "BREAKOUT / VWAP RECLAIM" if row["direction"] == "LONG" else "BREAKDOWN / VWAP LOSS"
            table.add_row(
                row["ticker"],
                f"{DIRECTION_EMOJI[row['direction']]} {row['direction']}",
                str(row["day_score"]),
                f"${plan['entry_low']:.2f}-${plan['entry_high']:.2f}",
                f"${plan['stop']:.2f}",
                f"${plan['tp1']:.2f}",
                f"${plan['tp2']:.2f}",
                f"1:{plan['rr']:.1f}" if plan["rr"] == plan["rr"] else "n/a",
                setup,
                "WAIT FOR CONFIRMATION",
            )
        console.print(table)
    else:
        header = (
            f"{'Symbol':<8}{'Dir':<7}{'Score':>6}  {'Entry':<18}{'Stop':>10}{'TP1':>10}{'TP2':>10}{'R:R':>7}  Setup"
        )
        print(header)
        print("-" * len(header))
        for row, plan in rows_with_plans:
            setup = "BREAKOUT/VWAP RECLAIM" if row["direction"] == "LONG" else "BREAKDOWN/VWAP LOSS"
            entry_str = f"${plan['entry_low']:.2f}-${plan['entry_high']:.2f}"
            rr_str = f"1:{plan['rr']:.1f}" if plan["rr"] == plan["rr"] else "n/a"
            print(
                f"{row['ticker']:<8}{row['direction']:<7}{row['day_score']:>6}  {entry_str:<18}"
                f"${plan['stop']:>9.2f}${plan['tp1']:>9.2f}${plan['tp2']:>9.2f}{rr_str:>7}  {setup}"
            )


DO_NOT_ENTER = """
DO NOT ENTER IF:
- gap > 5-7%
- price > 2 ATR from entry
- volume disappears (RVOL fades back under 1)
- loses VWAP
- market reverses
"""


def print_report(rows: list[dict], top: int) -> None:
    rows = sorted(rows, key=lambda r: r["day_score"], reverse=True)

    if HAS_RICH:
        console = Console(width=140)
        table = Table(title="Day Trading Scanner (1-5 day horizon)")
        for col in ("Symbol", "Price", "vs20MA", "ATR%", "RVOL", "Gap%", "Score", "Direction"):
            table.add_column(col, justify="right" if col not in ("Symbol", "Direction") else "left")
        for r in rows:
            table.add_row(
                r["ticker"],
                f"{r['price']:.2f}",
                fmt(r["dist_from_ma20"], "%"),
                "n/a" if r["atr_pct"] != r["atr_pct"] else f"{r['atr_pct']:.1f}%",
                "n/a" if r["rvol"] != r["rvol"] else f"{r['rvol']:.2f}x",
                fmt(r["gap_pct"], "%"),
                str(r["day_score"]),
                f"{DIRECTION_EMOJI[r['direction']]} {r['direction']}",
            )
        console.print(table)
    else:
        header = f"{'Symbol':<8}{'Price':>8}{'vs20MA':>9}{'ATR%':>7}{'RVOL':>7}{'Gap%':>8}{'Score':>7}  Direction"
        print(header)
        print("-" * len(header))
        for r in rows:
            atr_str = "n/a" if r["atr_pct"] != r["atr_pct"] else f"{r['atr_pct']:.1f}%"
            rvol_str = "n/a" if r["rvol"] != r["rvol"] else f"{r['rvol']:.2f}x"
            print(
                f"{r['ticker']:<8}{r['price']:>8.2f}{fmt(r['dist_from_ma20'], '%'):>9}"
                f"{atr_str:>7}{rvol_str:>7}{fmt(r['gap_pct'], '%'):>8}"
                f"{r['day_score']:>7}  {DIRECTION_EMOJI[r['direction']]} {r['direction']}"
            )

    longs = [r for r in rows if r["direction"] == "LONG"][:top]
    shorts = [r for r in rows if r["direction"] == "SHORT"][:top]

    print(f"\nTOP {top} DAY-TRADE LONG WATCH")
    print("-" * 40)
    for r in longs:
        print(f"{r['ticker']:<8}{r['day_score']:>4}/100   {DIRECTION_EMOJI['LONG']} LONG")

    if shorts:
        print(f"\nTOP {len(shorts)} DAY-TRADE SHORT WATCH")
        print("-" * 40)
        for r in shorts:
            print(f"{r['ticker']:<8}{r['day_score']:>4}/100   {DIRECTION_EMOJI['SHORT']} SHORT")

    print("\nTRADE PLANS")
    print("-" * 40)
    plans = [(r, plan) for r in longs + shorts for plan in [build_trade_plan(r)] if plan]
    print_trade_plans(plans)

    print(DO_NOT_ENTER)


def main() -> None:
    parser = argparse.ArgumentParser(description="Day Trading Score scanner (1-5 day horizon)")
    parser.add_argument("tickers", nargs="*", help="Explicit ticker list, overrides --tickers-file")
    parser.add_argument("--tickers-file", help="Path to a newline-separated ticker list (default: tickers.txt)")
    parser.add_argument("--catalysts", help="Path to a JSON file mapping ticker -> days until next catalyst")
    parser.add_argument("--top", type=int, default=20, help="How many LONG/SHORT setups to build trade plans for")
    args = parser.parse_args()

    tickers = load_tickers(args)
    catalysts = load_catalysts(args.catalysts)

    rows = []
    for ticker in tickers:
        result = analyze_day(ticker, catalysts.get(ticker))
        if result is None:
            print(f"skipping {ticker}: no data", file=sys.stderr)
            continue
        rows.append(result)

    if not rows:
        sys.exit("No tickers could be analyzed.")

    print_report(rows, top=args.top)


if __name__ == "__main__":
    main()
