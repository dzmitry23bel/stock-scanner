"""Shared configuration and input loading for all scanners."""
from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TICKERS_FILE = PROJECT_ROOT / "tickers.txt"


def load_tickers(args: Namespace) -> list[str]:
    if args.tickers:
        return [ticker.upper() for ticker in args.tickers]
    path = Path(args.tickers_file) if args.tickers_file else DEFAULT_TICKERS_FILE
    if not path.exists():
        sys.exit(f"Tickers file not found: {path}")
    return [
        line.strip().upper()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def load_catalysts(path: Optional[str]) -> dict[str, int]:
    if not path:
        return {}
    file = Path(path)
    if not file.exists():
        return {}
    data = json.loads(file.read_text())
    return {ticker.upper(): days for ticker, days in data.items() if not ticker.startswith("_")}