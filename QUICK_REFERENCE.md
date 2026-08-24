# Knife Catch Scanner - Quick Reference

## One-Liners

| Task | Command |
|------|---------|
| Scan all 142 tickers | `python knife_catch_scanner.py --top 50` |
| Scan specific tickers | `python knife_catch_scanner.py MRVL CRDO CGEM` |
| With catalysts bonus | `python knife_catch_scanner.py --catalysts catalysts.json` |
| Set up daily automation | `cp com.user.knife-catch-scanner.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.user.knife-catch-scanner.plist` |
| Check automation status | `launchctl list \| grep knife-catch` |
| View logs | `tail -f scan_results/scanner.log` |
| Unload automation | `launchctl unload ~/Library/LaunchAgents/com.user.knife-catch-scanner.plist` |

## Scoring Summary

| Score | Classification | Action |
|-------|-----------------|--------|
| **85-100** | 🟢 STRONG KNIFE CATCH | High conviction — Enter |
| **75-84** | 🟢 LONG CANDIDATE | Valid setup — Monitor & verify |
| **60-74** | 🟡 WAIT | Oversold but incomplete — Await confirmation |
| **<60** | 🔴 AVOID | Doesn't meet criteria — Skip |

## 8-Point Scoring Checklist

✓ = Points toward score | ✗ = No points

### 1. Long-Term Trend (15 pts max)
- [ ] Price > 200-SMA  
- [ ] 50-SMA > 200-SMA  
- [ ] 50-SMA not falling  

### 2. Correction Size (10 pts max)
- [ ] -5% to -25% drawdown from recent high  

### 3. Support Level (15 pts max)
- [ ] Within 10% of previous low  
- [ ] Within 8% of 200-SMA  
- [ ] Within 5% of 50-SMA  

### 4. Volume Exhaustion (15 pts max)
- [ ] Volume spike then decline pattern  
- [ ] Recent volume < 20-day average  
- [ ] Declining volume trend  

### 5. RSI/Divergence (10 pts max)
- [ ] RSI < 30 (or < 35)  
- [ ] Bullish RSI divergence  

### 6. Price Structure (15 pts max)
- [ ] Higher Low pattern formed  
- [ ] Bounce off recent low  

### 7. VWAP/EMA (10 pts max)
- [ ] Price >= VWAP  
- [ ] Price >= 20-EMA  
- [ ] Price >= 50-SMA  

### 8. Relative Strength (5 pts max)
- [ ] Falling less than SPY  
- [ ] Outperforming on recovery  

**TOTAL: 100 pts possible**

## Scanner Output Columns

```
Ticker    | Stock symbol
Score     | 0-100 knife catch score
Class     | 🟢 LONG CANDIDATE / 🟡 WAIT / 🔴 AVOID
Price     | Current price
Drawdown  | % decline from recent high
RSI       | Current RSI(14)
Entry     | Suggested entry (usually = current price)
Stop      | Stop loss (Entry - 2×ATR)
TP1       | First target (Entry + 2×ATR)
TP2       | Second target (Entry + 3.5×ATR)
R:R       | Risk/Reward ratio (TP2-Entry)/(Entry-Stop)
```

## Before You Enter Any Trade ⚠️

### Pre-Entry Checklist
- [ ] Scanner score >= 75 (🟢 LONG or STRONG)
- [ ] Confirmed on live chart (price, support, volume, structure)
- [ ] No negative news/catalysts since scanner ran
- [ ] Stock is liquid (>1M avg volume)
- [ ] R/R ratio acceptable (>1.5 minimum, ideally >2)
- [ ] Position size appropriate for your account
- [ ] Hard stop set at exact level (no "moving it")

### During Trade
- [ ] Monitor until TP1 hit
- [ ] Exit 50% at TP1, trail stop to breakeven for rest
- [ ] Monitor for news/gaps that invalidate trade
- [ ] NO averaging down if you're wrong
- [ ] Exit if stop hit = setup failed

## Common Mistakes to Avoid

❌ **Ignoring stops** → Account bleed
❌ **Trading illiquid stocks** → Can't exit at stop
❌ **Overdosing leverage** → ×5 leverage = ×5 losses
❌ **Checking daily** → It's a 1-5 day trade, don't micromanage
❌ **Fighting the stop** → If stop hits, you were wrong
❌ **Trading on news** → Wait for next scanner signal
❌ **No diversification** → Trade multiple setups, don't all-in one
❌ **Revenge trading** → Loss makes you angry → bigger loss

## Good Practices

✅ **Diversify signals** — Trade 3-5 setups simultaneously
✅ **Risk per trade** — 1-2% of account maximum
✅ **Track results** — Every trade in a log
✅ **Review weekly** — Win rate? Best/worst signals?
✅ **Adjust weights** — If something consistently fails, reduce its weight
✅ **Take profits** — Don't be greedy, 2x risk/reward is good
✅ **Hard stops** — No exceptions, ever
✅ **Verify charts** — Scanner is tool, not oracle

## Example Workflow

**4:15 PM (After market close)**
1. Run: `python knife_catch_scanner.py --top 50`
2. Review top 5 (score >= 75)
3. Pull chart for each, verify support/structure
4. Note 2-3 strong candidates for next day entry

**9:35 AM (Next day, after open)**
1. Check for any overnight gaps/news
2. If still valid, enter 1-2 candidates
3. Set stops immediately (non-negotiable)
4. Set TP alerts

**During day**
1. Exit 50% at TP1 if hit
2. Trail stop on remaining to breakeven
3. Let it ride if TP2 in reach

**After close**
1. Log trade result (entry, exit, PnL, duration)
2. Next day: repeat

## For the Impatient

**30-second version:**
1. `python knife_catch_scanner.py --top 5`
2. Pick top score >= 75
3. Check live chart (5 min)
4. If looks good + no bad news → Enter
5. Hard stop 2×ATR below entry
6. Target 2-3×ATR above entry

**That's it.** Everything else is optimization.

## Performance Tracking

Create `trade_log.csv`:
```
Date, Ticker, Score, Entry, TP1, TP2, Stop, Actual_Exit, Win/Loss, Duration, Notes
```

Monthly review:
- Win rate?
- Average R/R achieved?
- Which factors correlate with wins?
- Adjust weights next month based on data

## Project Structure

```
stock-scanner/
├── knife_catch_scanner.py          ← Main scanner
├── run_daily_scan.py               ← Automation wrapper
├── com.user.knife-catch-scanner.plist ← macOS scheduler
├── tickers.txt                     ← Your 142 tickers
├── catalysts.example.json          ← Optional catalyst bonuses
├── requirements.txt                ← Dependencies
├── KNIFE_CATCH_README.md           ← Technical details
├── KNIFE_CATCH_GUIDE.md            ← Full user guide
├── scan_results/                   ← Auto-created
│   ├── knife_catch_history.csv     ← Signal log
│   ├── scan_YYYYMMDD_HHMMSS.txt    ← Detailed results
│   ├── scanner.log                 ← Daily log
│   └── scanner_error.log           ← Error log
└── .venv/                          ← Virtual environment
```

## Need Help?

- **How to enter a trade?** → See "Step-by-Step" in KNIFE_CATCH_GUIDE.md
- **Why is score low?** → Check which factors failed in detailed output
- **How to adjust scoring?** → Edit weights in knife_catch_scanner.py (search "Factor")
- **Automation not working?** → `launchctl load -w` to debug, check .plist syntax
- **Tickers missing?** → Add to tickers.txt, one per line

---

## Quick Start (3 Steps)

1. **Install**: `pip install -r requirements.txt`
2. **Test**: `python knife_catch_scanner.py GOOGL MPWR`
3. **Run**: `python knife_catch_scanner.py --top 50`

## That's All You Need to Know 🎯

The scanner does the heavy lifting. Your job:
1. Run it
2. Pick high scores (>75)
3. Verify on chart
4. Enter + hard stop
5. Trail to target
6. Track result

Everything else is noise.

---

**Last Updated**: 2026-08-24  
**Status**: Production-ready ✅
