# Stock Entry Scanner Suite

A comprehensive multi-strategy Python toolkit for identifying trading opportunities across 156 stocks via Yahoo Finance. Three separate scanners for different time horizons and risk profiles.

```
Yahoo Finance → Technical Analysis → 0-100 Scores → Trade Classification
```

**Ticker Universe:** 156 stocks (142 core + 14 new: WOLF, TWST, MSTR, BTDR, CHTR, ACN, EPAM, LENZ, TOYO, NRDS, TSLA, SMR, TDUP, CRVS)

## Quick Start

```bash
# Install
cd stock-scanner
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run knife catch scanner (most popular)
python knife_catch_scanner.py --top 50

# Or run trend/momentum scanner
python scanner.py --top 50

# Or run day trading scanner
python day_trade.py --top 20
```

---

## Scanner #1: Knife Catch Scanner (Reversal Detection)

**Best for:** 1-5 day swing trades, identifying oversold reversals

Detects sharp price declines showing signs of exhaustion and potential reversal using 8 independent factors.

### Scoring System (0-100)

| Factor | Points | Criteria |
|--------|--------|----------|
| Long-term Trend | 15 | Price > 200-SMA, 50-SMA > 200-SMA, 50-SMA not falling |
| Correction Size | 10 | Drawdown magnitude from recent high (-5% to -25%) |
| Support Level | 15 | Proximity to key levels (previous lows, SMAs) |
| Volume Exhaustion | 15 | Initial spike then declining volume pattern |
| RSI/Divergence | 10 | RSI < 35, bullish divergence detection |
| Price Structure | 15 | Higher low pattern, bounce off recent low |
| VWAP/EMA Reclaim | 10 | Price above VWAP, 20-EMA, 50-SMA |
| Relative Strength | 5 | Outperformance vs SPY |

### Classifications

```
85-100  →  🟢 STRONG KNIFE CATCH      (High conviction entry)
75-84   →  🟢 LONG CANDIDATE           (Valid setup)
60-74   →  🟡 WAIT                     (Oversold, needs confirmation)
<60     →  🔴 AVOID                    (Lacks reversal criteria)
```

### Usage

```bash
# Scan all 156 tickers, show top 50
python knife_catch_scanner.py --top 50

# Specific tickers
python knife_catch_scanner.py GOOGL MPWR MRVL

# With catalyst bonuses
python knife_catch_scanner.py --catalysts catalysts.json --top 50
```

### Example Output

```
GOOGL    80/100   🟢 LONG CANDIDATE
Entry   $344.82
Stop    $328.24
TP1     $361.40
TP2     $373.84
R/R     1 : 1.75

✓ Strong long-term trend
✓ -15% from recent high
✓ Support detected
✓ Volume exhaustion
✓ RSI oversold
✓ Higher Low pattern
✓ VWAP reclaim
✓ Relative strength
```

### Entry/Stop/TP Calculation

- **Entry:** Current price
- **Stop Loss:** Entry - (2 × ATR)
- **TP1:** Entry + (2 × ATR)
- **TP2:** Entry + (3.5 × ATR)
- **R/R:** (TP2 - Entry) / (Entry - Stop)

**Documentation:** See [KNIFE_CATCH_GUIDE.md](KNIFE_CATCH_GUIDE.md), [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

---

## Scanner #2: Trend/Momentum Scanner (Growth Setups)

**Best for:** 5-30 day swing trades, uptrend pullbacks, momentum breakouts

Scores stocks on trend sustainability, momentum, pullback quality, and risk factors.

### Scoring System (0-100)

- **Trend (30):** Price > 200-MA, 50-MA > 200-MA, MAs rising
- **Momentum (25):** Positive 1M/3M/6M/1Y/3Y returns
- **Pullback (25):** Price near 50-MA, off recent high, 1W down / 1M up
- **Risk (20):** Above 200-MA, not overextended vs 50-MA, no blow-off, normal volatility
- **Catalyst bonus:** Optional, from `catalysts.json`

### Classifications

- 🟢 **BUY DIP** – Strong uptrend + pullback to 50-MA (ideal entry)
- 🟢 **MOMENTUM BUY** – Strong uptrend + breakout + RVOL > 1.3x
- 🟡 **WAIT** – Strong trend but overextended (>15% above 50-MA)
- 🟡 **WATCH** – Uptrend without clear entry yet
- 🔴 **AVOID** – Below both MAs with negative momentum

### Usage

```bash
python scanner.py                       # scan tickers.txt
python scanner.py AAPL NVDA CGEM        # scan explicit list
python scanner.py --tickers-file mylist.txt
python scanner.py --catalysts catalysts.json --top 30
```

---

## Scanner #3: Day Trading Scanner (Intraday/Leveraged)

**Best for:** 1-5 day trades with 2-5x leverage, intraday patterns

Short-horizon, volume/momentum focused scanner for leveraged positions.

### Scoring System (0-100)

- **Momentum:** 25% (recent price action)
- **Trend:** 20% (MA alignment, direction)
- **Entry:** 20% (pullback quality, support)
- **Volume:** 15% (RVOL, intraday volume)
- **Catalyst:** 10% (upcoming events)
- **Risk:** 10% (ATR, recent volatility)

### Classifications

- 🟢 **LONG** – High probability setup for ×5 leverage
- 🔴 **SHORT** – Downside reversal, short setup
- 🟡 **WAIT** – Promising but incomplete

### Usage

```bash
python day_trade.py                              # scan tickers.txt
python day_trade.py MRVL AAPL CRDO
python day_trade.py --catalysts catalysts.json --top 20 --leverage 5
```

### Output Includes

- Entry zone (current price)
- Stop loss (2× ATR below)
- TP1 and TP2 (2-3.5× ATR above)
- R/R ratio
- ATR-based position sizing

**Note:** VWAP, opening-range, RVOL estimated from Yahoo Finance 5-minute bars (best-effort). Always confirm live before entering leveraged trades.

---

## Automation

### Daily Scanning (via launchd)

Set up automatic daily scans at 4:10 PM ET (market close):

```bash
# Copy and load
cp com.user.knife-catch-scanner.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.knife-catch-scanner.plist

# Check status
launchctl list | grep knife-catch

# View logs
tail -f scan_results/scanner.log

# Unload
launchctl unload ~/Library/LaunchAgents/com.user.knife-catch-scanner.plist
```

### Manual Daily Run

```bash
python run_daily_scan.py
```

Logs results to `scan_results/knife_catch_history.csv` and saves detailed reports.

---

## Configuration

### Catalysts Bonus

Create `catalysts.json` to add bonus points to certain tickers:

```json
{
  "AAPL": 10,
  "NVDA": 15,
  "TSLA": 8
}
```

Then run:
```bash
python knife_catch_scanner.py --catalysts catalysts.json
```

### Custom Ticker List

Edit `tickers.txt` (one ticker per line) or use:

```bash
python knife_catch_scanner.py --tickers-file my_custom_list.txt
```

---

## File Structure

```
stock-scanner/
├── knife_catch_scanner.py          # Main reversal scanner (500+ lines)
├── scanner.py                      # Trend/momentum scanner
├── day_trade.py                    # Day trading scanner
├── run_daily_scan.py               # Daily automation wrapper
├── tickers.txt                     # 156 tickers (updated)
├── catalysts.example.json          # Optional catalyst config
├── requirements.txt                # Dependencies
├── README.md                       # This file
├── KNIFE_CATCH_README.md           # Technical docs
├── KNIFE_CATCH_GUIDE.md            # Complete user guide
├── QUICK_REFERENCE.md              # Cheat sheet
├── SETUP.sh                        # Setup instructions
├── com.user.knife-catch-scanner.plist # macOS automation
└── scan_results/                   # Auto-created directory
    ├── knife_catch_history.csv     # Signal log
    ├── scan_YYYYMMDD_HHMMSS.txt    # Detailed results
    ├── scanner.log                 # Daily automation log
    └── scanner_error.log           # Error log
```

---

## Key Differences Between Scanners

| Feature | Knife Catch | Trend/Momentum | Day Trading |
|---------|-------------|---|---|
| **Time Horizon** | 1-5 days | 5-30 days | 1-5 days |
| **Strategy** | Oversold reversal | Uptrend continuation | Momentum/leverage |
| **Factors** | 8 (structure-focused) | 4 (trend-focused) | 6 (volume-focused) |
| **Leverage** | 1-2x | 1x | 2-5x |
| **Best For** | Catching bounces | Riding trends | Day trades |
| **Entry Type** | Support bounce | Pullback to MA | Volume breakout |

---

## Tips

### 1. Verify on Live Charts

Scanner is a starting point. Always check:
- Support/resistance visualization
- Volume pattern confirmation
- No negative news/catalysts
- Liquidity (>1M avg volume)

### 2. Track Performance

Log every trade:
```csv
Date, Ticker, Scanner, Entry, Exit, PnL, Win/Loss
```

Review monthly for optimization.

### 3. Combine Signals

Best trades often have signals from **multiple scanners**. Example:
- Knife Catch: 80/100
- Trend/Momentum: BUY DIP
- Day Trading: LONG

= Very high conviction setup

### 4. Adjust for Market Regime

- **Bull market:** Knife catches + Momentum buys work best
- **Bear market:** Day trading shorts + oversold bounces
- **Choppy market:** Wait for clearer signals, skip tight setups

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `yfinance not found` | `pip install -r requirements.txt` |
| Scanner too slow | Runs 1 year of data for 156 tickers (~10 min first time) |
| Some tickers showing AVOID | Normal! Only high-quality setups shown |
| No STRONG signals found | Market conditions don't support many reversals right now |
| Automation not working | Check `launchctl list`, verify .plist syntax, check logs |

---

## Dependencies

```
yfinance>=0.2.40
pandas>=2.0
numpy>=1.24
rich>=13.0
```

---

## Next Steps

1. **Scan today:** `python knife_catch_scanner.py --top 50`
2. **Review top 5** (score >= 75)
3. **Verify on charts** (support, volume, structure)
4. **Paper trade 1-2 setups** to validate
5. **Track results** in CSV
6. **Optimize** based on win rate

---

**Status:** ✅ Production-ready  
**Last Updated:** 2026-08-24  
**Ticker Universe:** 156 (updated)

