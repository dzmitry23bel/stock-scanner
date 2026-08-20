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
