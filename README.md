# Stock Scanner Suite

Python toolkit for scanning a shared universe of US stocks with three independent strategies. Data comes from Yahoo Finance and each strategy returns a 0-100 score plus a trade classification.

```text
Yahoo Finance -> scanner strategy -> score -> ranked report
```

The default universe is maintained in [`tickers.txt`](tickers.txt). The project currently contains 156 tickers.

## Quick Start

```bash
cd stock-scanner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run all strategies and show the top 50 from each
python run_all_scanners.py --top 50
```

The master report shows each scanner separately with its signal and trade levels.

## Strategies

### 1. Knife Catch: Reversal

Module: [`scanners/knife_catch_scanner.py`](scanners/knife_catch_scanner.py)

Horizon: 1-5 days. Looks for an oversold decline that may be exhausting near support.

The score combines long-term trend, correction size, support, volume exhaustion, RSI/divergence, higher-low structure, VWAP/EMA reclaim, and relative strength versus SPY. It also calculates ATR-based entry, stop, and profit targets.

```bash
python knife_catch_scanner.py --top 50
python knife_catch_scanner.py GOOGL MPWR MRVL
```

Classifications: `STRONG KNIFE CATCH`, `LONG CANDIDATE`, `WAIT`, `AVOID`.

Detailed documentation: [`KNIFE_CATCH_GUIDE.md`](KNIFE_CATCH_GUIDE.md) and [`KNIFE_CATCH_README.md`](KNIFE_CATCH_README.md).

### 2. Trend/Momentum: Growth

Module: [`scanners/long_term_scanner.py`](scanners/long_term_scanner.py)

Horizon: 5-30 days. Measures trend alignment, multi-period momentum, pullback quality, and risk.

```bash
python long_term_scanner.py
python long_term_scanner.py AAPL NVDA CGEM
python long_term_scanner.py --tickers-file my_tickers.txt --catalysts catalysts.json
```

Classifications: `BUY DIP`, `MOMENTUM BUY`, `WATCH`, `WAIT`, `AVOID`.

### 3. Day Trading: Intraday Setups

Module: [`scanners/short_term_scanner.py`](scanners/short_term_scanner.py)

Horizon: 1-5 days, with optional leverage. Uses daily momentum/trend, ATR, pullback entry, intraday VWAP, opening range, RVOL, gap, and catalyst data.

```bash
python short_term_scanner.py --top 20
python short_term_scanner.py MRVL AAPL CRDO --catalysts catalysts.json
```

Classifications: `LONG`, `SHORT`, `WAIT`. Intraday Yahoo Finance data is best-effort and must be confirmed with a live feed before trading.

## Master Scanner

[`run_all_scanners.py`](run_all_scanners.py) is the recommended entry point. It imports all three strategies directly, ranks each result, and prints separate tables with signal and trade levels.

```bash
python run_all_scanners.py              # top 50 per scanner
python run_all_scanners.py --top 20     # top 20 per scanner
python run_all_scanners.py --catalysts catalysts.json
```

`--top` controls the number of results retained from each strategy. The report displays up to 15 rows per strategy so the terminal remains readable.

## Configuration

### Tickers

Edit [`tickers.txt`](tickers.txt), one symbol per line. Lines beginning with `#` are ignored. Individual scanner commands also accept explicit tickers or `--tickers-file`.

### Catalysts

Copy [`catalysts.example.json`](catalysts.example.json) and provide days until the next catalyst:

```json
{
  "AAPL": 7,
  "NVDA": 3,
  "TSLA": 14
}
```

Pass the file with `--catalysts`. Catalyst bonuses are strategy-specific.

## Project Layout

```text
stock-scanner/
├── scanners/
│   ├── __init__.py           # Scanner package
│   ├── common.py             # Shared ticker and catalyst loading
│   ├── knife_catch_scanner.py        # Reversal scanner
│   ├── long_term_scanner.py     # Growth scanner
│   └── short_term_scanner.py          # Intraday/day-trade scanner
├── run_all_scanners.py       # Unified report for all strategies
├── run_daily_scan.py         # Knife-catch logging automation
├── scanner.py                # Compatibility CLI wrapper
├── short_term_scanner.py              # Compatibility CLI wrapper
├── knife_catch_scanner.py    # Compatibility CLI wrapper
├── tickers.txt               # Default ticker universe
├── catalysts.example.json    # Catalyst file template
├── requirements.txt          # Python dependencies
├── scan_results/             # Generated reports and history
└── com.user.knife-catch-scanner.plist  # macOS launchd job
```

The three root-level scanner files are intentionally small compatibility wrappers. New code should import from `scanners`.

## Daily Automation

### GitHub Actions

[`daily-scan.yml`](.github/workflows/daily-scan.yml) runs automatically on weekdays at 10:30 America/New_York, approximately one hour after the NYSE open. It handles daylight-saving time by using two UTC cron slots and runs only when the NYSE calendar is open. A manual run is also available from the Actions tab.

Each successful run saves timestamped Markdown, JSON, and standalone HTML reports under [`scan_results/ci/`](scan_results/ci/), then commits them back to the repository. The HTML report contains only actionable signals such as `LONG CANDIDATE`, `BUY DIP`, `MOMENTUM BUY`, `LONG`, and `SHORT`; `WAIT`, `WATCH`, and `AVOID` are excluded to keep it readable. Every listed row includes the ticker, score, signal, Entry, Stop, TP1, and TP2 when an actionable plan exists.

Run a single logged knife-catch scan:

```bash
python run_daily_scan.py
```

To use macOS `launchd`:

```bash
cp com.user.knife-catch-scanner.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.knife-catch-scanner.plist
launchctl list | grep knife-catch
launchctl unload ~/Library/LaunchAgents/com.user.knife-catch-scanner.plist
```

Reports and CSV history are written to `scan_results/`. Master Markdown, JSON, and HTML reports are stored separately under `scan_results/master/` for local runs and `scan_results/ci/` for GitHub Actions runs.

## Data and Risk Notes

- The scanners are research and ranking tools, not financial advice.
- Yahoo Finance can return delayed, missing, or rate-limited data.
- Scores are relative technical signals, not guarantees of future returns.
- Confirm price, volume, VWAP, liquidity, spread, and risk limits before entering a position.
- Leveraged trades can lose capital quickly; use position sizing and predefined stops.