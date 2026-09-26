#!/usr/bin/env python3
"""Stock Entry Scanner.

Pulls historical prices from Yahoo Finance, computes trend/momentum/pullback/risk
scores and classifies each ticker as BUY DIP / MOMENTUM BUY / WATCH / WAIT / AVOID.

Usage:
    python long_term_scanner.py                              # scan tickers.txt
    python long_term_scanner.py AAPL NVDA CGEM               # scan an explicit list
    python long_term_scanner.py --tickers-file mylist.txt
    python long_term_scanner.py --catalysts catalysts.json   # add catalyst score bonus
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from .common import load_catalysts, load_tickers

try:
    from rich.console import Console
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

DEFAULT_TICKERS_FILE = Path(__file__).resolve().parent.parent / "data" / "tickers.txt"

# Trading-day windows used for the return columns.
RETURN_WINDOWS = {"1W": 5, "1M": 21, "3M": 63, "6M": 126, "1Y": 252, "3Y": 756}


def pct_change_over(close: pd.Series, days: int) -> float:
    if len(close) <= days:
        return float("nan")
    return float((close.iloc[-1] / close.iloc[-1 - days] - 1) * 100)


def fetch_history(ticker: str) -> Optional[pd.DataFrame]:
    try:
        df = yf.Ticker(ticker).history(period="4y", auto_adjust=True)
    except Exception:
        return None
    return df if not df.empty else None


def compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    high, low, close = df["High"], df["Low"], df["Close"]
    previous_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1
    ).max(axis=1)
    return float(true_range.rolling(period).mean().iloc[-1])


def classify(
    *,
    trend_score: int,
    returns: dict[str, float],
    vs_50ma: float,
    rel_volume: float,
    near_high: bool,
    price: float,
    ma50: float,
    ma200: float,
) -> str:
    below_200 = price < ma200 if ma200 == ma200 else False
    ma50_below_ma200 = (ma50 < ma200) if (ma50 == ma50 and ma200 == ma200) else False
    strong_uptrend = trend_score >= 20

    if below_200 and ma50_below_ma200 and returns["1M"] < 0 and returns["1Y"] < 0:
        return "AVOID"
    if (
        strong_uptrend
        and returns["1W"] < 0
        and returns["1M"] > 0
        and abs(vs_50ma) <= 5
        and price > ma200
    ):
        return "BUY DIP"
    if strong_uptrend and returns["1M"] > 10 and near_high and rel_volume == rel_volume and rel_volume > 1.3:
        return "MOMENTUM BUY"
    if strong_uptrend and vs_50ma > 15:
        return "WAIT"
    if strong_uptrend:
        return "WATCH"
    return "AVOID" if below_200 else "WATCH"



def _fundamental_component(value: object, *, good: float, excellent: float, bad: float, reverse: bool = False) -> float:
    """Map a numeric fundamental metric to 0..100; missing data is neutral."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return 50.0
    if not np.isfinite(x):
        return 50.0
    if reverse:
        if x <= good:
            return 100.0
        if x <= excellent:
            return 80.0
        if x >= bad:
            return 15.0
        return 50.0
    if x >= excellent:
        return 100.0
    if x >= good:
        return 80.0
    if x <= bad:
        return 15.0
    return 50.0


def fetch_fundamentals(ticker: str) -> dict:
    """Fetch a compact fundamental snapshot from Yahoo Finance."""
    try:
        info = yf.Ticker(ticker).info
    except Exception:
        return {}
    return {
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "profit_margin": info.get("profitMargins"),
        "operating_margin": info.get("operatingMargins"),
        "roe": info.get("returnOnEquity"),
        "free_cash_flow": info.get("freeCashflow"),
        "debt_to_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "forward_pe": info.get("forwardPE"),
        "market_cap": info.get("marketCap"),
    }


def quality_score(f: dict) -> float:
    """Business-quality score, separate from price/timing."""
    parts = [
        _fundamental_component(f.get("revenue_growth"), good=0.05, excellent=0.15, bad=-0.10),
        _fundamental_component(f.get("earnings_growth"), good=0.05, excellent=0.20, bad=-0.15),
        _fundamental_component(f.get("profit_margin"), good=0.08, excellent=0.20, bad=-0.05),
        _fundamental_component(f.get("operating_margin"), good=0.10, excellent=0.25, bad=0.0),
        _fundamental_component(f.get("roe"), good=0.10, excellent=0.20, bad=-0.05),
        _fundamental_component(f.get("free_cash_flow"), good=0.0, excellent=1.0, bad=-1.0),
        _fundamental_component(f.get("debt_to_equity"), good=50.0, excellent=25.0, bad=200.0, reverse=True),
        _fundamental_component(f.get("current_ratio"), good=1.0, excellent=2.0, bad=0.5),
    ]
    return round(float(np.mean(parts)), 1)


def analyze(ticker: str, catalyst_days: Optional[int]) -> Optional[dict]:
    df = fetch_history(ticker)
    if df is None or len(df) < 60:
        return None

    close = df["Close"]
    volume = df["Volume"]
    price = float(close.iloc[-1])
    atr = compute_atr(df)

    ma50 = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    ma50_now = float(ma50.iloc[-1])
    ma200_now = float(ma200.iloc[-1]) if len(close) >= 200 else float("nan")
    ema20_now = float(ema20.iloc[-1])
    ema50_now = float(ema50.iloc[-1])
    vs_ema20 = (price / ema20_now - 1) * 100
    vs_ema50 = (price / ema50_now - 1) * 100
    ema20_rising = ema20.iloc[-1] > ema20.iloc[-6]
    ema50_rising = ema50.iloc[-1] > ema50.iloc[-6]

    returns = {label: pct_change_over(close, days) for label, days in RETURN_WINDOWS.items()}

    ma50_rising = ma50.dropna().shape[0] > 5 and ma50.iloc[-1] > ma50.iloc[-6]
    ma200_rising = ma200.dropna().shape[0] > 5 and ma200.iloc[-1] > ma200.iloc[-6]

    recent_high = float(close.tail(252).max())
    near_high = price >= recent_high * 0.97

    vs_50ma = (price / ma50_now - 1) * 100
    vs_200ma = (price / ma200_now - 1) * 100 if ma200_now == ma200_now else float("nan")

    avg_vol_20d = float(volume.tail(20).mean())
    rel_volume = float(volume.iloc[-1] / avg_vol_20d) if avg_vol_20d else float("nan")

    vol_20d = float(close.pct_change().tail(20).std() * np.sqrt(252) * 100)

    # --- EMA timing / pullback zone ---
    if price > ma200_now and ema50_rising and ema50_now > ma200_now:
        if -6 <= vs_ema50 <= 3:
            ema_zone = "IDEAL_EMA50"
            ema_timing = 100.0
        elif -8 <= vs_ema20 <= 2:
            ema_zone = "EMA20_PULLBACK"
            ema_timing = 90.0
        elif vs_ema50 > 12:
            ema_zone = "EXTENDED"
            ema_timing = 35.0
        else:
            ema_zone = "TREND"
            ema_timing = 65.0
    elif price > ma200_now and vs_ema50 < 0:
        ema_zone = "DEEP_PULLBACK"
        ema_timing = 75.0 if ema50_rising else 55.0
    elif price > ma200_now:
        ema_zone = "RECOVERY"
        ema_timing = 60.0
    else:
        ema_zone = "BELOW_200"
        ema_timing = 20.0

    fundamentals = fetch_fundamentals(ticker)
    quality = quality_score(fundamentals)

    # --- Trend (30) ---
    trend = 0
    trend += 10 if price > ma200_now else 0
    trend += 10 if (ma50_now == ma50_now and ma200_now == ma200_now and ma50_now > ma200_now) else 0
    trend += 5 if ma50_rising else 0
    trend += 5 if ma200_rising else 0

    # --- Momentum (25) ---
    momentum = sum(5 for k in ("1M", "3M", "6M", "1Y", "3Y") if returns.get(k, float("nan")) > 0)

    # --- Pullback (25) ---
    pullback = 0
    pullback += 10 if abs(vs_50ma) <= 5 else 0
    pullback += 5 if price < recent_high * 0.98 else 0
    pullback += 5 if returns["1W"] < 0 else 0
    pullback += 5 if returns["1M"] > 0 else 0

    # --- Risk (20) ---
    risk = 0
    risk += 5 if price > ma200_now else 0
    risk += 5 if abs(vs_50ma) <= 15 else 0
    risk += 5 if returns["1M"] < 50 else 0
    risk += 5 if vol_20d < 60 else 0

    technical_score = trend + momentum + pullback + risk

    catalyst_bonus = 0
    if catalyst_days is not None:
        if catalyst_days <= 7:
            catalyst_bonus = 8
        elif catalyst_days <= 30:
            catalyst_bonus = 5
    # The scanner now separates company quality from market timing.
    # Quality matters, but a great company at an extended price is still a WAIT.
    timing_score = min(100.0, max(0.0, 0.55 * technical_score + 0.45 * ema_timing))
    final_score = min(
        100,
        round(0.35 * quality + 0.40 * timing_score + 0.15 * technical_score + 0.10 * min(100, catalyst_bonus * 10), 1),
    )

    situation = classify(
        trend_score=trend,
        returns=returns,
        vs_50ma=vs_50ma,
        rel_volume=rel_volume,
        near_high=near_high,
        price=price,
        ma50=ma50_now,
        ma200=ma200_now,
    )

    return {
        "ticker": ticker,
        "price": price,
        "atr": atr,
        "returns": returns,
        "vs_50ma": vs_50ma,
        "vs_200ma": vs_200ma,
        "ema20": ema20_now,
        "ema50": ema50_now,
        "vs_ema20": vs_ema20,
        "vs_ema50": vs_ema50,
        "ema_zone": ema_zone,
        "ema_timing_score": round(ema_timing, 1),
        "quality_score": quality,
        "fundamentals": fundamentals,
        "rel_volume": rel_volume,
        "technical_score": technical_score,
        "catalyst_bonus": catalyst_bonus,
        "final_score": final_score,
        "situation": situation,
    }


SITUATION_EMOJI = {
    "BUY DIP": "🟢",
    "MOMENTUM BUY": "🟢",
    "WATCH": "🟡",
    "WAIT": "🟡",
    "AVOID": "🔴",
}


def trend_emoji(value: float, positive_threshold: float = 0.0) -> str:
    if value != value:  # NaN
        return "⚪"
    return "🟢" if value >= positive_threshold else "🔴"


def fmt_pct(value: float) -> str:
    return "n/a" if value != value else f"{value:+.1f}%"


def print_report(rows: list[dict]) -> None:
    rows = sorted(rows, key=lambda r: r["final_score"], reverse=True)

    if HAS_RICH:
        console = Console(width=140)
        table = Table(title="Stock Entry Scanner")
        for col in ("Symbol", "Price", "1W", "1M", "1Y", "vs 50MA", "vs 200MA", "RelVol", "Trend", "Score", "Setup"):
            table.add_column(col, justify="right" if col not in ("Symbol", "Setup") else "left")
        for r in rows:
            trend_str = f"{trend_emoji(r['vs_50ma'])}{trend_emoji(r['vs_200ma'])}"
            table.add_row(
                r["ticker"],
                f"{r['price']:.2f}",
                fmt_pct(r["returns"]["1W"]),
                fmt_pct(r["returns"]["1M"]),
                fmt_pct(r["returns"]["1Y"]),
                fmt_pct(r["vs_50ma"]),
                fmt_pct(r["vs_200ma"]),
                "n/a" if r["rel_volume"] != r["rel_volume"] else f"{r['rel_volume']:.2f}x",
                trend_str,
                str(r["final_score"]),
                f"{SITUATION_EMOJI.get(r['situation'], '')} {r['situation']}",
            )
        console.print(table)
    else:
        header = f"{'Symbol':<8}{'Price':>8}{'1W':>8}{'1M':>8}{'1Y':>8}{'vs50MA':>9}{'vs200MA':>10}{'RelVol':>8}{'Score':>7}  Setup"
        print(header)
        print("-" * len(header))
        for r in rows:
            rel_vol_str = "n/a" if r["rel_volume"] != r["rel_volume"] else f"{r['rel_volume']:.2f}x"
            print(
                f"{r['ticker']:<8}{r['price']:>8.2f}{fmt_pct(r['returns']['1W']):>8}"
                f"{fmt_pct(r['returns']['1M']):>8}{fmt_pct(r['returns']['1Y']):>8}"
                f"{fmt_pct(r['vs_50ma']):>9}{fmt_pct(r['vs_200ma']):>10}"
                f"{rel_vol_str:>8}"
                f"{r['final_score']:>7}  {SITUATION_EMOJI.get(r['situation'], '')} {r['situation']}"
            )

    def bucket(name: str) -> list[dict]:
        return [r for r in rows if r["situation"] == name]

    print("\nTOP BUY SETUPS")
    print("-" * 40)
    for r in bucket("BUY DIP") + bucket("MOMENTUM BUY"):
        print(f"{r['ticker']:<8}{r['final_score']:>4}/100   {SITUATION_EMOJI[r['situation']]} {r['situation']}")

    print("\nWAIT / WATCH")
    print("-" * 40)
    for r in bucket("WAIT") + bucket("WATCH"):
        print(f"{r['ticker']:<8}{r['final_score']:>4}/100   {SITUATION_EMOJI[r['situation']]} {r['situation']}")

    print("\nAVOID")
    print("-" * 40)
    for r in bucket("AVOID"):
        print(f"{r['ticker']:<8}{r['final_score']:>4}/100   {SITUATION_EMOJI[r['situation']]} {r['situation']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Stock Entry Scanner")
    parser.add_argument("tickers", nargs="*", help="Explicit ticker list, overrides --tickers-file")
    parser.add_argument("--tickers-file", help="Path to a newline-separated ticker list (default: tickers.txt)")
    parser.add_argument("--catalysts", help="Path to a JSON file mapping ticker -> days until next catalyst")
    args = parser.parse_args()

    tickers = load_tickers(args)
    catalysts = load_catalysts(args.catalysts)

    rows = []
    for ticker in tickers:
        result = analyze(ticker, catalysts.get(ticker))
        if result is None:
            print(f"skipping {ticker}: no data", file=sys.stderr)
            continue
        rows.append(result)

    if not rows:
        sys.exit("No tickers could be analyzed.")

    print_report(rows)


if __name__ == "__main__":
    main()
