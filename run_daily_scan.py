#!/usr/bin/env python3
"""Daily automation script for knife catch scanner.

Runs the scanner daily and logs results to CSV for tracking accuracy
and performance over time.

Usage:
    python run_daily_scan.py                    # Single run
    
    # Cron: Run daily at market close (4 PM EST = 8 PM UTC, 9 PM EDT)
    0 21 * * 1-5 cd /path/to/stock-scanner && /usr/bin/python3 run_daily_scan.py
    
    # Or: Schedule via launchd (macOS) using run_daily_scan.plist
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_SCANNER_DIR = Path(__file__).parent
RESULTS_DIR = DEFAULT_SCANNER_DIR / "scan_results"
RESULTS_CSV = RESULTS_DIR / "knife_catch_history.csv"


def ensure_results_dir() -> None:
    """Create results directory if it doesn't exist."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_scanner(top_n: int = 50, catalysts: str | None = None) -> dict:
    """Execute the knife catch scanner and return results."""
    cmd = [
        sys.executable,
        str(DEFAULT_SCANNER_DIR / "knife_catch_scanner.py"),
        "--top", str(top_n)
    ]
    
    if catalysts:
        cmd.extend(["--catalysts", catalysts])
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=DEFAULT_SCANNER_DIR)
    
    if result.returncode != 0:
        print(f"Error running scanner: {result.stderr}", file=sys.stderr)
        return {}
    
    return {"stdout": result.stdout, "stderr": result.stderr}


def parse_scanner_output(output: str) -> list[dict]:
    """Parse scanner output and extract signals (basic parsing)."""
    # This is a simplified parser. For production, consider JSON output from scanner
    signals = []
    lines = output.split('\n')
    
    for line in lines:
        # Look for lines with ticker, score, classification
        parts = line.split()
        if parts and parts[0].isupper() and parts[0] not in ["KNIFE", "Ticker"]:
            try:
                ticker = parts[0]
                score = float(parts[1]) if len(parts) > 1 else 0
                signals.append({
                    "ticker": ticker,
                    "score": score,
                    "timestamp": datetime.now().isoformat()
                })
            except (ValueError, IndexError):
                pass
    
    return signals


def log_signals_to_csv(signals: list[dict]) -> None:
    """Log signals to CSV for tracking."""
    ensure_results_dir()
    
    file_exists = RESULTS_CSV.exists()
    
    with open(RESULTS_CSV, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'ticker', 'score', 'date'])
        
        if not file_exists:
            writer.writeheader()
        
        for signal in signals:
            writer.writerow({
                'timestamp': signal['timestamp'],
                'ticker': signal['ticker'],
                'score': signal['score'],
                'date': datetime.now().strftime('%Y-%m-%d')
            })
    
    print(f"Logged {len(signals)} signals to {RESULTS_CSV}")


def save_scan_report(output: str) -> None:
    """Save full scanner output to timestamped file."""
    ensure_results_dir()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = RESULTS_DIR / f"scan_{timestamp}.txt"
    
    report_file.write_text(output)
    print(f"Saved detailed report to {report_file}")


def main():
    print(f"\n{'=' * 80}")
    print(f"KNIFE CATCH DAILY SCAN - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}\n")
    
    # Check if catalysts file exists
    catalysts_file = DEFAULT_SCANNER_DIR / "catalysts.json"
    catalysts_arg = str(catalysts_file) if catalysts_file.exists() else None
    
    # Run scanner
    result = run_scanner(top_n=50, catalysts=catalysts_arg)
    
    if not result:
        print("Scanner failed to run", file=sys.stderr)
        sys.exit(1)
    
    output = result.get("stdout", "")
    
    # Parse and log
    signals = parse_scanner_output(output)
    if signals:
        log_signals_to_csv(signals)
    
    # Save detailed report
    save_scan_report(output)
    
    # Print summary
    print(f"\n✓ Scan complete!")
    print(f"  - Signals found: {len(signals)}")
    print(f"  - Report saved to: {RESULTS_DIR}")
    print(f"  - History CSV: {RESULTS_CSV}")


if __name__ == "__main__":
    main()
