"""Yahoo Finance analyst consensus helpers.

Analyst data is optional enrichment. Scanner operation does not depend on it.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import yfinance as yf


def _num(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def fetch_analyst_target(ticker: str) -> dict[str, Any]:
    """Return normalized Yahoo analyst consensus target data."""
    try:
        data = yf.Ticker(ticker).get_analyst_price_targets() or {}
    except Exception:
        return {
            "ticker": ticker,
            "target_available": False,
            "source": "yahoo_finance",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    current = _num(data.get("current"))
    low = _num(data.get("low"))
    high = _num(data.get("high"))
    mean = _num(data.get("mean"))
    median = _num(data.get("median"))

    upside_pct = None
    if current and median is not None:
        upside_pct = (median / current - 1.0) * 100.0

    return {
        "ticker": ticker,
        "target_available": median is not None or mean is not None,
        "source": "yahoo_finance",
        "current": current,
        "low": low,
        "high": high,
        "mean": mean,
        "median": median,
        "upside_pct": upside_pct,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_analyst_targets(tickers: list[str], max_workers: int = 8) -> dict[str, dict[str, Any]]:
    """Fetch targets in parallel and isolate per-ticker failures."""
    results: dict[str, dict[str, Any]] = {}
    unique = list(dict.fromkeys(str(t).upper().strip() for t in tickers if str(t).strip()))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_analyst_target, ticker): ticker for ticker in unique}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                results[ticker] = future.result()
            except Exception:
                results[ticker] = {
                    "ticker": ticker,
                    "target_available": False,
                    "source": "yahoo_finance",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
    return results
