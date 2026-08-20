# Stock Entry Scanner

Scans a list of tickers via Yahoo Finance and scores each one on trend,
momentum, pullback and risk to flag good entry setups.

```
Yahoo Finance -> prices/volume -> technical score (0-100) -> setup classification
```

## Setup

```bash
cd stock-scanner
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python scanner.py                       # scan tickers.txt
python scanner.py AAPL NVDA CGEM        # scan an explicit list
python scanner.py --tickers-file mylist.txt
cp catalysts.example.json catalysts.json  # edit with real catalyst dates
python scanner.py --catalysts catalysts.json
```

## Scoring

- **Trend (30):** price > 200MA, 50MA > 200MA, MAs rising
- **Momentum (25):** positive 1M/3M/6M/1Y/3Y returns
- **Pullback (25):** price near 50MA, off recent high, 1W down / 1M up
- **Risk (20):** above 200MA, not overextended vs 50MA, no blow-off move, normal volatility
- **Catalyst bonus:** optional, from `catalysts.json` (ticker -> days to next catalyst)

## Setups

- 🟢 **BUY DIP** – strong uptrend + short-term pullback near 50MA
- 🟢 **MOMENTUM BUY** – strong uptrend + breakout + relative volume > 1.3x
- 🟡 **WAIT** – strong trend but >15% above 50MA (overextended)
- 🟡 **WATCH** – uptrend without a clear entry signal yet
- 🔴 **AVOID** – below both MAs with negative 1M/1Y momentum

## Day trading (1-5 day, leveraged)

`day_trade.py` is a separate scanner for short-horizon, leveraged setups. It
computes its own 0-100 Day Score (Momentum 25% / Trend 20% / Entry 20% /
Volume 15% / Catalyst 10% / Risk 10%), classifies each ticker LONG / SHORT /
WAIT, and prints an ATR-based trade plan (entry zone, stop, TP1, TP2, R:R)
for the top setups.

```bash
python day_trade.py                              # scan tickers.txt
python day_trade.py MRVL AAPL CRDO
python day_trade.py --catalysts catalysts.json --top 20 --leverage 5
```

VWAP, opening-range and RVOL are estimated from Yahoo Finance 5-minute bars
for the most recent session (best-effort, not a real-time feed) — always
confirm live price/VWAP/volume before entering a leveraged trade.

