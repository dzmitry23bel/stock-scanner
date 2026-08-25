# Knife Catch Scanner - Complete User Guide

## What is a "Knife Catch"?

A **knife catch** is a high-probability reversal trade that targets stocks in sharp decline that show signs of exhaustion and reversal. The term comes from "catching a falling knife" — buying a stock that's dropped sharply.

### Why It Works

1. **Sharp declines often overshoot** — Panic selling takes prices too far down
2. **Exhaustion patterns are detectable** — Volume spike then collapse signals selling is done
3. **Support levels provide reference** — Technical levels tell us where buyers might emerge
4. **Oversold indicators cluster** — RSI < 30, price far below moving averages, volume declining
5. **Reversals offer edge** — Risk/reward is favorable: tight stops, 2-3x potential upside

### When It's Dangerous

❌ **Broken trends** — Stock fundamentally broken, trend still down
❌ **Catalyst gaps** — Major negative news/earnings miss
❌ **No support** — Price below all key levels with no floor
❌ **Increasing volume** — Heavy selling still ongoing
❌ **Relative weakness** — Stock down more than SPY/sector

## How the Scanner Works

### 1. Hard Filters (Must Pass All)

Before even scoring, the scanner checks:

✓ **Sufficient historical data** — At least 60 days available
✓ **Reasonable liquidity** — Enough volume to enter/exit

If these fail → Skip ticker entirely

### 2. Soft Scoring (8 Factors)

For passing tickers, compute a 0-100 score:

#### **Factor 1: Long-Term Trend Confirmation (15 points)**
```
✓ Price > 200-day SMA              (+5 points)
✓ 50-day SMA > 200-day SMA         (+5 points)
✓ 50-day SMA not falling           (+5 points)
```

**Why?** Entry is more reliable when the long-term trend is intact. We're not fighting the trend, just catching a pullback.

#### **Factor 2: Correction Magnitude (10 points)**
```
-5%  from recent high   → 2 points
-8%  from recent high   → 5 points
-15% from recent high   → 8 points
-25% from recent high   → 10 points (cap)
```

**Why?** Bigger drops have more potential upside, but also more risk. We weight it but don't overindex.

#### **Factor 3: Support Level Proximity (15 points)**
```
Price within 10% of previous low   → +5 points
Price within 8% of 200-SMA         → +5 points
Price within 5% of 50-SMA          → +5 points
```

**Why?** Support is where buyers show up. Closer = more likely bounce.

#### **Factor 4: Volume Exhaustion (15 points)**
```
Detected volume spike then decline  → +5 points
Recent volume < 20-day average      → +5 points
Recent volumes declining trend      → +5 points
```

**Why?** Volume exhaustion signals selling is done. If volume is still high, selling continues.

#### **Factor 5: RSI / Divergence (10 points)**
```
RSI < 30  → +7 points
RSI < 35  → +5 points
RSI < 40  → +2 points

Bullish divergence detected → +5 points
```

**Why?** RSI < 30 is mathematically oversold (mean reversion). Divergence = price makes lower low, but RSI makes higher low = hidden strength.

#### **Factor 6: Price Structure (15 points)**
```
Higher Low pattern detected        → +10 points
Recent bounce off recent low        → +5 points
```

**Why?** Higher low = buyers stepped in, preventing lower lows. Bullish structure.

#### **Factor 7: VWAP / EMA Reclaim (10 points)**
```
Price >= VWAP              → +5 points
Price >= 20-day EMA        → +3 points
Price >= 50-day SMA        → +2 points
```

**Why?** Recovery through key moving averages confirms the reversal is real, not just a bounce.

#### **Factor 8: Relative Strength vs SPY (5 points)**
```
Stock down less than SPY           → +5 points
Stock outperforming on recovery    → +3 points
```

**Why?** If your stock is falling less than the market, it has relative strength. Good sign.

### 3. Final Score & Classification

```
85-100  →  🟢 STRONG KNIFE CATCH      (High conviction, consider entry)
75-84   →  🟢 LONG CANDIDATE           (Valid setup, good risk/reward)
60-74   →  🟡 WAIT                     (Oversold but structure incomplete)
<60     →  🔴 AVOID                    (Lacks knife catch criteria)
```

## Risk/Reward Calculation

For each signal, the scanner calculates entry/stop/target levels sized off **ATR (14-period)**.

```
ATR = Average True Range (volatility measure)

Entry Price     = Current Price
Stop Loss       = Entry - (2 × ATR)     ← Tight stop, ~2% of price
TP1             = Entry + (2 × ATR)     ← First target
TP2             = Entry + (3.5 × ATR)   ← Second target

Risk/Reward = (TP2 - Entry) / (Entry - Stop)
```

**Example: GOOGL**
```
Current Price: $344.82
ATR:           $8.29

Entry:  $344.82
Stop:   $328.24  (down 4.6%)
TP1:    $361.40  (up 4.8%)
TP2:    $373.84  (up 8.4%)

R/R = $29.02 / $16.58 = 1.75  (Good 1:1.75 risk/reward)
```

## Usage Examples

### 1. Daily Scan (All 142 Tickers)

```bash
python knife_catch_scanner.py --top 50
```

Output: Top 50 tickers sorted by score. Shows:
- Ticker, Score, Classification
- Entry, Stop, TP1, TP2, R/R ratio
- Supporting factors (✓ checks)

### 2. Scan Specific Tickers

```bash
python knife_catch_scanner.py MRVL CRDO CGEM GPCR
```

Good for:
- Checking your watchlist
- Validating a ticker before entry
- Comparing a few candidates

### 3. Add Catalyst Bonuses

```bash
python knife_catch_scanner.py --catalysts catalysts.json --top 50
```

If `catalysts.json` contains:
```json
{
  "AAPL": 10,
  "NVDA": 15,
  "CGEM": 8
}
```

These tickers get bonus points (capped at +20).

### 4. Automated Daily Scanning

```bash
# One-time setup
cp config/com.user.knife-catch-scanner.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/config/com.user.knife-catch-scanner.plist

# Scanner runs automatically at 4:10 PM ET every weekday
# Results saved to: reports/daily/scan_YYYYMMDD_HHMMSS.txt
```

## Step-by-Step: Trading a Knife Catch Signal

### 1. **Review Scanner Output**

```
GOOGL    80/100   🟢 LONG CANDIDATE
Entry   $344.82
Stop    $328.24
TP1     $361.40
TP2     $373.84
R/R     1 : 1.75

✓ Strong long-term trend
✓ -15% from recent high
✓ Support at 50-SMA
✓ Volume exhaustion
✓ RSI at 32
✓ Higher Low confirmed
✓ VWAP reclaim
✓ Relative strength improving
```

✓ **75+** score = worth investigating further

### 2. **Verify on Live Chart**

Pull up the chart (TradingView, your broker, etc.):

- [ ] **Trend**: Price > 200 SMA? 50 SMA > 200? Visually confirm
- [ ] **Support**: Is current price actually near support level shown?
- [ ] **Volume**: Does recent volume show exhaustion pattern?
- [ ] **RSI**: Is RSI indeed < 35? Any divergence visible?
- [ ] **Structure**: Do you see the higher low pattern?
- [ ] **VWAP**: Is price approaching/above VWAP?
- [ ] **No news**: Any negative catalysts/gaps since scanner run?

### 3. **Check Fundamentals** (Optional but Recommended)

- [ ] No recent catastrophic news (bankruptcy, audit failures, etc.)
- [ ] Company doesn't look broken
- [ ] Sector sentiment OK (not getting hammered)

### 4. **Execute Trade**

**Position Size** (adjust to your risk tolerance):
- **Conservative**: 1-2 contracts (if options) or 0.5-1% portfolio risk
- **Moderate**: 2-3 contracts or 1-2% portfolio risk
- **Aggressive**: 3-5 contracts (with leverage) or 2-5% portfolio risk

**Entry**:
- Market order at current price (if volume is good)
- Limit order near support (if you want to be picky)

**Stop Loss**:
- HARD STOP at level calculated by scanner
- Do NOT move it lower ("giving it more room")
- Exit if stop is hit = the setup is invalidated

**Take Profit**:
- Exit 50% at TP1
- Trail the remaining 50% to TP2 or breakeven

### 5. **Track Result**

Log the trade:
```
Date:        2026-08-24
Ticker:      GOOGL
Signal:      LONG CANDIDATE (80/100)
Entry:       $344.82
Exit (TP1):  $361.40  → +$16.58 / +4.8%
Exit (TP2):  $373.84  → +$29.02 / +8.4%
Stop Hit:    NO
Result:      ✓ WIN
R/R:         1.75
Duration:    2 days
```

Track over time to validate the scanner's accuracy.

## Important Warnings ⚠️

### 1. **Not Every Knife Catch Works**
Success rate is typically 60-70%. No strategy is perfect. Size accordingly.

### 2. **Catalyst Blindness**
The scanner is technical. It can't see:
- Negative earnings surprise
- Investigation/lawsuit announcement
- Product recall
- CEO departure

**Always check news** before entering.

### 3. **Intraday Gaps**
Stock might gap down open next day, invalidating your stop. Consider gapping risk on your sizing.

### 4. **Liquidity Matters**
Trade only liquid stocks (>1M avg volume). Illiquid stocks can gap and trap you.

### 5. **Leverage Amplifies Losses**
If using ×5 leverage:
- Winner of ×5 = 5x reward
- BUT loser of ×5 = 5x loss
- Stick to small position sizes
- Hard stops are ESSENTIAL

### 6. **Market Regime**
Knife catches work best in correcting markets. In a bear market collapse, they fail.

## Optimization Ideas

### Track Performance
Modify `scripts/run_daily_scan.py` to log results to CSV. Then monthly:
- Win rate?
- Average R/R?
- Which factors matter most?

### Weight Adjustment
Start with default weights, then adjust based on live results:
- If support matters more than RSI for your tickers → increase weight
- If volume exhaustion is noise → decrease weight

### Add More Factors
- Earnings calendar (avoid earnings day)
- Institutional ownership (big holders = support)
- Put/call ratio (options sentiment)
- Market breadth (market correction depth)

### Multiple Timeframes
- Daily knife catches (1-5 day hold)
- Intraday knife catches (×5 lever, 1-hour pattern)
- Weekly knife catches (longer term, lower risk)

## Files Reference

| File | Purpose |
|------|---------|
| `knife_catch_scanner.py` | Main scanner (run this) |
| `scripts/run_daily_scan.py` | Automation wrapper |
| `../config/com.user.knife-catch-scanner.plist` | macOS launchd config (optional) |
| `KNIFE_CATCH_README.md` | Technical documentation |
| `data/tickers.txt` | List of 142 tickers to scan |
| `../config/catalysts.example.json` | Template for catalyst bonuses |
| `../reports/daily/` | Auto-created directory for logs |

## Troubleshooting

### Error: "yfinance module not found"
```bash
pip install -r requirements.txt
# Or: pip install yfinance pandas numpy rich
```

### Scanner takes too long
- It fetches 1 year of data for 142 tickers (~5-10 min first run)
- Subsequent runs are faster (cached)
- Run during off-market hours

### Some tickers show as AVOID
- Means they don't currently meet knife catch criteria
- This is OK! You want high-conviction signals only
- Check again tomorrow

### No STRONG KNIFE CATCHES found
- Normal! Market conditions determine how many form
- In choppy/bull market: fewer knife catches
- In declining market: more knife catches

## Next Steps

1. **Run today**: `python knife_catch_scanner.py --top 50`
2. **Review top 5 scores >= 75**
3. **Verify on live charts** (very important!)
4. **Paper trade 1-2 signals** to validate
5. **Track results** in a log or spreadsheet
6. **Optimize** based on what works

---

**Questions?** Review the code comments in `knife_catch_scanner.py` or test with small positions first.

**Happy knife catching!** 🎣📈

---
Last Updated: 2026-08-24
