# Knife Catch Scanner - Automated Reversal Detection

A sophisticated Python-based scanner that identifies oversold reversal opportunities across your 142 tickers using a quantitative 0-100 scoring system.

## Strategy Overview

The **Knife Catch** strategy targets stocks in a confirmed downtrend that show signs of potential reversal through:

- **Trend confirmation** — Long-term uptrend still intact
- **Significant drawdown** — Sharp decline from recent highs
- **Support identification** — Price near key support levels (SMAs, previous lows)
- **Volume exhaustion** — Initial high volume selloff followed by declining volume
- **Oversold indicators** — RSI < 35 + potential bullish divergence
- **Price structure** — Higher low pattern formation
- **VWAP/EMA reclaim** — Price recovering above key moving averages
- **Relative strength** — Stock outperforming SPY in recovery

## Scoring System

Each stock receives a 0-100 score based on 8 weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Long-term Trend | 15 | Price > 200 SMA, 50 SMA > 200 SMA, 50 SMA not falling |
| Correction Size | 10 | Drawdown magnitude from recent high (-8%, -15%, -25%, etc.) |
| Support | 15 | Proximity to support levels (previous lows, SMA200/50) |
| Volume Exhaustion | 15 | Initial spike then declining volume pattern |
| RSI/Divergence | 10 | RSI < 35, bullish divergence detection |
| Price Structure | 15 | Higher low pattern, bounce off recent low |
| VWAP/EMA Reclaim | 10 | Price above VWAP, 20-EMA, 50-SMA |
| Relative Strength | 5 | Performance vs SPY during correction |
| **TOTAL** | **100** | **Final Score** |

## Classification Levels

| Score | Classification | Action |
|-------|-----------------|--------|
| 85-100 | 🟢 **STRONG KNIFE CATCH** | High-conviction reversal setup — Consider entry |
| 75-84 | 🟢 **LONG CANDIDATE** | Valid setup with good risk/reward — Monitor closely |
| 60-74 | 🟡 **WAIT** | Oversold but structure incomplete — Await confirmation |
| <60 | 🔴 **AVOID** | Lacks knife catch criteria — Skip or hold |

## Entry/Stop/TP Levels

For each signal, the scanner calculates:

- **Entry Price** — Current price
- **Stop Loss** — Entry - (2 × ATR)
- **TP1** — Entry + (2 × ATR)
- **TP2** — Entry + (3.5 × ATR)
- **Risk/Reward Ratio** — Calculated from above

Sizing should be position-based off your leverage (×5 for short-term, ×1-2 for swing).

## Usage

### Scan All 142 Tickers (Top 50 Results)
```bash
python knife_catch_scanner.py --top 50
```

### Scan Specific Tickers
```bash
python knife_catch_scanner.py MRVL CRDO CGEM
```

### Add Catalyst Bonuses
```bash
python knife_catch_scanner.py --catalysts catalysts.json --top 50
```

### Scan From Custom List
```bash
python knife_catch_scanner.py --tickers-file my_tickers.txt
```

## Example Output

```
KNIFE CATCH SCANNER
────────────────────────────────────────────

GOOGL    80/100   🟢 LONG CANDIDATE
Entry   $344.82
Stop    $328.24
TP1     $361.40
TP2     $373.84
R/R     1 : 2.0

✓ Strong long-term trend
✓ -15% from recent high
✓ Support at 50-SMA
✓ Volume exhaustion pattern
✓ RSI at 32 (oversold)
✓ Higher low confirmed
✓ VWAP reclaim
✓ Relative strength vs SPY

────────────────────────────────────────────

MPWR    77/100   🟢 LONG CANDIDATE
Entry   $89.34
Stop    $76.21
TP1     $102.47
TP2     $115.60
R/R     1 : 1.8

GE      68/100   🟡 WAIT
Entry   $156.34
Stop    $142.98
TP1     $169.70
TP2     $183.06
R/R     1 : 1.5

✓ Oversold (RSI 28)
✓ Support detected

✗ No Higher Low yet
✗ VWAP not reclaimed

WAIT FOR CONFIRMATION BEFORE ENTRY

────────────────────────────────────────────
```

## Key Features

✅ **Quantitative Analysis** — No guessing or opinions; 0-100 scoring

✅ **Hard Filters + Soft Scoring** — Only analyzes fundamentally sound stocks

✅ **Real Market Data** — Yahoo Finance OHLCV, volume, and technical indicators

✅ **Risk-Aware Sizing** — ATR-based stops and targets for consistent risk/reward

✅ **Multi-factor Confirmation** — Requires multiple bullish signals, not just one

✅ **Relative Strength** — Considers outperformance vs SPY

## Important Notes

⚠️ **Not Guarant eed** — No indicator is perfect. This is a high-probability setup, not a certainty.

⚠️ **Catalyst Check** — Always cross-check for negative news/catalysts before entry.

⚠️ **Liquidity** — Only trade liquid stocks (avg volume > 1M shares).

⚠️ **Live Confirmation** — Always verify support/volume/price in real-time before entering.

⚠️ **Risk Management** — Use position sizing and strict stops. Leverage amplifies losses.

## Modes (Future Enhancement)

### Daily Mode (Current)
- Scanning for next-day setups
- Uses daily OHLCV data
- Best for swing trading (1-5 days)

### Intraday Mode (Planned)
- Uses 5m/15m candles
- Includes opening range, RVOL, premarket data
- Best for ×5 leveraged intraday trades

## Implementation Details

The scanner:
1. Fetches 1 year of daily data from Yahoo Finance
2. Calculates SMAs (20, 50, 200), RSI, ATR, VWAP
3. Detects support/resistance from 60-bar lookback
4. Scores each factor independently
5. Sums scores and classifies
6. Calculates risk/reward entry points
7. Outputs ranked table + detailed breakdowns

## Files

- `knife_catch_scanner.py` — Main scanner script
- `data/tickers.txt` — List of 142 tickers to scan
- `../config/catalysts.example.json` — Optional catalyst bonus config
- `KNIFE_CATCH_README.md` — This file

## Requirements

```
yfinance>=0.2.40
pandas>=2.0
numpy>=1.24
rich>=13.0
```

Install: `pip install -r requirements.txt`

## Next Steps

1. **Run daily** — Scan every day at market close or pre-market
2. **Log signals** — Keep a CSV of all signals and their results
3. **Track accuracy** — Monitor win rate and risk/reward
4. **Iterate scoring** — Adjust weights based on live results
5. **Add more factors** — Earnings calendar, institutional ownership, etc.

---

**Status**: Production-ready for daily scanning.

**Last Updated**: 2026-08-24
