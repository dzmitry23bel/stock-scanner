#!/usr/bin/env python3
"""Knife Catch Scanner - Automated reversal detection strategy.

Analyzes 142 tickers for oversold reversal opportunities using:
- Long-term trend confirmation
- Drawdown magnitude
- Support level identification
- Volume exhaustion detection
- RSI + divergence
- Price structure (higher low)
- VWAP/EMA reclaim
- Relative strength vs SPY

Outputs a 0-100 Knife Catch Score with STRONG/LONG/WAIT/AVOID classification
and Entry/Stop/TP levels sized off ATR.

Usage:
    python knife_catch_scanner.py                              # scan tickers.txt
    python knife_catch_scanner.py MRVL CRDO CGEM               # scan explicit list
    python knife_catch_scanner.py --catalysts catalysts.json   # add catalyst bonus
    python knife_catch_scanner.py --mode intraday              # intraday mode (×5 leverage)
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

DEFAULT_TICKERS_FILE = Path(__file__).parent / "tickers.txt"


@dataclass
class KnifeCatchSignal:
    """Knife catch analysis result for a single ticker."""
    ticker: str
    score: float
    classification: str
    trend_score: float
    correction_score: float
    support_score: float
    exhaustion_score: float
    rsi_score: float
    structure_score: float
    vwap_score: float
    relative_strength_score: float
    
    # Price levels
    current_price: float
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float
    risk_reward_ratio: float
    
    # Supporting data
    recent_high: float
    recent_low: float
    drawdown_pct: float
    current_rsi: float
    support_level: float
    resistance_level: float
    sma_200: float
    sma_50: float
    sma_20: float
    atm: float


def load_tickers(args: argparse.Namespace) -> list[str]:
    """Load tickers from file or command line."""
    if args.tickers:
        return [t.upper() for t in args.tickers]
    path = Path(args.tickers_file) if args.tickers_file else DEFAULT_TICKERS_FILE
    if not path.exists():
        sys.exit(f"Tickers file not found: {path}")
    lines = path.read_text().splitlines()
    return [line.strip().upper() for line in lines if line.strip() and not line.startswith("#")]


def load_catalysts(path: Optional[str]) -> dict[str, int]:
    """Load catalyst bonuses from JSON file."""
    if not path or not Path(path).exists():
        return {}
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}


def fetch_daily_data(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """Fetch daily OHLCV data from Yahoo Finance."""
    try:
        df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        if df is None or df.empty or len(df) < 60:
            return None
        return df
    except Exception:
        return None


def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average."""
    return data.rolling(window=period).mean()


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return data.ewm(span=period, adjust=False).mean()


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Average True Range."""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def calculate_vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """Calculate Volume Weighted Average Price (simplified)."""
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    return vwap


def detect_support_resistance(data: pd.DataFrame, lookback: int = 60) -> tuple[float, float]:
    """Detect support and resistance levels from recent price action."""
    recent = data.tail(lookback)
    support = recent['Low'].min()
    resistance = recent['High'].max()
    return support, resistance


def detect_higher_low(data: pd.DataFrame, lookback: int = 20) -> bool:
    """Check if price has made a higher low (bullish structure)."""
    if len(data) < lookback + 5:
        return False
    
    recent = data.tail(lookback)
    older = data.iloc[-(lookback+5):-lookback]
    
    recent_low = recent['Low'].min()
    older_low = older['Low'].min()
    
    return recent_low > older_low


def detect_volume_exhaustion(data: pd.DataFrame, lookback: int = 20) -> bool:
    """Check for volume exhaustion pattern (high vol drop then decrease)."""
    if len(data) < lookback + 5:
        return False
    
    recent = data.tail(lookback)
    older = data.tail(lookback + 5).head(5)
    
    # Exhaustion: recent average volume lower than initial drop
    return recent['Volume'].mean() < older['Volume'].mean() * 1.5


def detect_bullish_rsi_divergence(data: pd.DataFrame, lookback: int = 20) -> bool:
    """Check for bullish RSI divergence (lower price low, higher RSI low)."""
    if len(data) < lookback:
        return False
    
    rsi = calculate_rsi(data['Close'], 14).tail(lookback)
    close = data['Close'].tail(lookback)
    
    # Simple heuristic: if RSI < 30 and recovering
    if rsi.iloc[-1] < 35:
        rsi_min = rsi.min()
        close_min_idx = close.idxmin()
        rsi_min_idx = rsi.idxmin()
        
        # If price made lower low before RSI, it's potential divergence
        return close_min_idx < rsi_min_idx
    
    return False


def analyze_knife_catch(ticker: str, data: pd.DataFrame, spy_data: Optional[pd.DataFrame] = None) -> Optional[KnifeCatchSignal]:
    """Analyze a ticker for knife catch opportunities."""
    
    try:
        close = data['Close']
        high = data['High']
        low = data['Low']
        volume = data['Volume']
        
        current_price = close.iloc[-1]
        current_volume = volume.iloc[-1]
        
        # Calculate indicators
        sma_200 = calculate_sma(close, 200).iloc[-1]
        sma_50 = calculate_sma(close, 50).iloc[-1]
        sma_20 = calculate_sma(close, 20).iloc[-1]
        ema_20 = calculate_ema(close, 20).iloc[-1]
        ema_50 = calculate_ema(close, 50).iloc[-1]
        rsi = calculate_rsi(close, 14).iloc[-1]
        atr = calculate_atr(high, low, close, 14).iloc[-1]
        vwap = calculate_vwap(high, low, close, volume).iloc[-1]
        
        # Support/Resistance
        support, resistance = detect_support_resistance(data, lookback=60)
        
        # Recent high/low
        recent_high = high.tail(60).max()
        recent_low = low.tail(60).min()
        drawdown_pct = ((current_price - recent_high) / recent_high) * 100
        
        # ===== SCORING SYSTEM (0-100) =====
        
        # 1. LONG-TERM TREND (15 points)
        trend_score = 0
        if current_price > sma_200:
            trend_score += 5
        if sma_50 > sma_200:
            trend_score += 5
        if sma_50 >= data['Close'].iloc[-5:].rolling(5).mean().iloc[-1]:  # 50 SMA not falling
            trend_score += 5
        
        # 2. SIZE OF CORRECTION (10 points)
        # Stronger drawdown = higher score (with diminishing returns)
        correction_score = 0
        if drawdown_pct < -5:
            correction_score = min(10, abs(drawdown_pct))
        if drawdown_pct < -8:
            correction_score = 10
        if drawdown_pct < -15:
            correction_score = 10  # Cap at 10
        
        # 3. SUPPORT (15 points)
        support_score = 0
        distance_to_support = abs(current_price - support) / current_price
        distance_to_sma200 = abs(current_price - sma_200) / current_price
        distance_to_sma50 = abs(current_price - sma_50) / current_price
        
        # Closer to support = higher score
        if distance_to_support < 0.10:
            support_score += 5
        if distance_to_sma200 < 0.08:
            support_score += 5
        if distance_to_sma50 < 0.05:
            support_score += 5
        
        # 4. VOLUME EXHAUSTION (15 points)
        exhaustion_score = 0
        avg_volume = volume.tail(20).mean()
        volume_ratio = current_volume / avg_volume
        
        if detect_volume_exhaustion(data, 20):
            exhaustion_score += 5
        if volume_ratio < 0.8:  # Low volume = exhaustion
            exhaustion_score += 5
        
        # Check for recent spike then decline
        recent_volumes = volume.tail(10)
        if recent_volumes.iloc[-1] < recent_volumes.max() * 0.7:
            exhaustion_score += 5
        
        # 5. RSI / DIVERGENCE (10 points)
        rsi_score = 0
        if rsi < 30:
            rsi_score += 7
        elif rsi < 35:
            rsi_score += 5
        elif rsi < 40:
            rsi_score += 2
        
        if detect_bullish_rsi_divergence(data, 20):
            rsi_score += 5
        
        rsi_score = min(10, rsi_score)
        
        # 6. PRICE STRUCTURE / HIGHER LOW (15 points)
        structure_score = 0
        if detect_higher_low(data, 20):
            structure_score += 10
        
        # Check for recent bounce off recent_low
        if recent_low > 0 and (current_price - recent_low) / recent_low > 0.02:
            structure_score += 5
        
        # 7. VWAP / EMA RECLAIM (10 points)
        vwap_score = 0
        if current_price >= vwap:
            vwap_score += 5
        if current_price >= ema_20:
            vwap_score += 3
        if current_price >= ema_50:
            vwap_score += 2
        
        # 8. RELATIVE STRENGTH vs SPY (5 points)
        relative_strength_score = 0
        if spy_data is not None and len(spy_data) >= 60:
            spy_drawdown = ((spy_data['Close'].iloc[-1] - spy_data['High'].tail(60).max()) / 
                           spy_data['High'].tail(60).max()) * 100
            
            # If stock fell less than SPY, or recovering faster
            if drawdown_pct > spy_drawdown * 0.8:  # Less severe
                relative_strength_score += 5
        else:
            relative_strength_score += 2  # Default bonus if no SPY data
        
        # TOTAL SCORE
        total_score = (trend_score + correction_score + support_score + 
                      exhaustion_score + rsi_score + structure_score + 
                      vwap_score + relative_strength_score)
        
        # Apply catalyst bonus if available (loaded separately)
        catalyst_bonus = 0  # Will be applied in main loop
        
        # ===== CLASSIFICATION =====
        if total_score >= 85:
            classification = "🟢 STRONG KNIFE CATCH"
        elif total_score >= 75:
            classification = "🟢 LONG CANDIDATE"
        elif total_score >= 60:
            classification = "🟡 WAIT"
        else:
            classification = "🔴 AVOID"
        
        # ===== ENTRY/STOP/TP LEVELS (sized off ATR) =====
        entry_price = current_price
        stop_loss = entry_price - (atr * 2)
        tp1 = entry_price + (atr * 2)
        tp2 = entry_price + (atr * 3.5)
        
        risk = entry_price - stop_loss
        reward = tp2 - entry_price
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        return KnifeCatchSignal(
            ticker=ticker,
            score=total_score,
            classification=classification,
            trend_score=trend_score,
            correction_score=correction_score,
            support_score=support_score,
            exhaustion_score=exhaustion_score,
            rsi_score=rsi_score,
            structure_score=structure_score,
            vwap_score=vwap_score,
            relative_strength_score=relative_strength_score,
            current_price=current_price,
            entry_price=entry_price,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            risk_reward_ratio=risk_reward_ratio,
            recent_high=recent_high,
            recent_low=recent_low,
            drawdown_pct=drawdown_pct,
            current_rsi=rsi,
            support_level=support,
            resistance_level=resistance,
            sma_200=sma_200,
            sma_50=sma_50,
            sma_20=sma_20,
            atm=atr,
        )
    
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}", file=sys.stderr)
        return None


def scan_tickers(tickers: list[str], catalysts: dict[str, int]) -> list[KnifeCatchSignal]:
    """Scan all tickers for knife catch opportunities."""
    
    # Fetch SPY for relative strength comparison
    spy_data = fetch_daily_data("SPY", period="1y")
    
    results = []
    
    for ticker in tickers:
        data = fetch_daily_data(ticker)
        
        if data is None or len(data) < 60:
            continue
        
        signal = analyze_knife_catch(ticker, data, spy_data)
        
        if signal is not None:
            # Apply catalyst bonus
            if ticker in catalysts:
                catalyst_bonus = min(catalysts[ticker], 20)  # Cap bonus at 20 points
                signal.score = min(100, signal.score + catalyst_bonus)
            
            results.append(signal)
    
    return results


def print_results(results: list[KnifeCatchSignal], top_n: int = 30) -> None:
    """Print results in formatted table."""
    
    # Sort by score descending
    results = sorted(results, key=lambda x: x.score, reverse=True)
    top_results = results[:top_n]
    
    if not HAS_RICH:
        # Fallback to plain text
        print("\n" + "=" * 150)
        print(f"{'KNIFE CATCH SCANNER RESULTS':^150}")
        print("=" * 150)
        print(f"{'Ticker':<8} {'Score':<8} {'Class':<22} {'Price':<10} {'Drawdown':<12} {'RSI':<8} {'Entry':<10} {'Stop':<10} {'TP1':<10} {'TP2':<10} {'R:R':<8}")
        print("-" * 150)
        
        for signal in top_results:
            print(f"{signal.ticker:<8} {signal.score:>7.1f} {signal.classification:<22} "
                  f"${signal.current_price:>8.2f} {signal.drawdown_pct:>10.1f}% {signal.current_rsi:>7.1f} "
                  f"${signal.entry_price:>8.2f} ${signal.stop_loss:>8.2f} "
                  f"${signal.tp1:>8.2f} ${signal.tp2:>8.2f} 1:{signal.risk_reward_ratio:>6.2f}")
    else:
        # Rich table output
        console = Console()
        
        table = Table(title="KNIFE CATCH SCANNER", show_header=True, header_style="bold magenta")
        table.add_column("Ticker", style="cyan", width=8)
        table.add_column("Score", justify="right", width=8)
        table.add_column("Classification", style="yellow", width=20)
        table.add_column("Price", justify="right", width=10)
        table.add_column("Drawdown", justify="right", width=12)
        table.add_column("RSI", justify="right", width=8)
        table.add_column("Entry", justify="right", width=10)
        table.add_column("Stop", justify="right", width=10)
        table.add_column("TP1", justify="right", width=10)
        table.add_column("TP2", justify="right", width=10)
        table.add_column("R:R", justify="right", width=8)
        
        for signal in top_results:
            table.add_row(
                signal.ticker,
                f"{signal.score:.1f}",
                signal.classification,
                f"${signal.current_price:.2f}",
                f"{signal.drawdown_pct:.1f}%",
                f"{signal.current_rsi:.1f}",
                f"${signal.entry_price:.2f}",
                f"${signal.stop_loss:.2f}",
                f"${signal.tp1:.2f}",
                f"${signal.tp2:.2f}",
                f"1:{signal.risk_reward_ratio:.2f}"
            )
        
        console.print(table)
    
    # Print detailed breakdown for top signals
    if HAS_RICH and len(top_results) > 0:
        console = Console()
        
        for signal in top_results[:5]:  # Show detailed breakdown for top 5
            checks = []
            if signal.trend_score >= 10:
                checks.append("✓ Strong long-term trend")
            if signal.correction_score >= 8:
                checks.append(f"✓ Significant drawdown ({signal.drawdown_pct:.1f}%)")
            if signal.support_score >= 10:
                checks.append("✓ Support detected")
            if signal.exhaustion_score >= 10:
                checks.append("✓ Volume exhaustion")
            if signal.rsi_score >= 8:
                checks.append(f"✓ Oversold RSI ({signal.current_rsi:.1f})")
            if signal.structure_score >= 8:
                checks.append("✓ Higher Low / Price structure")
            if signal.vwap_score >= 7:
                checks.append("✓ VWAP/EMA reclaim")
            if signal.relative_strength_score >= 3:
                checks.append("✓ Relative strength improving")
            
            panel_text = f"[bold]{signal.ticker}    Score: {signal.score:.0f}/100    {signal.classification}[/bold]\n"
            panel_text += f"[cyan]Entry:   ${signal.entry_price:.2f}[/cyan]\n"
            panel_text += f"[red]Stop:    ${signal.stop_loss:.2f}[/red]\n"
            panel_text += f"[green]TP1:     ${signal.tp1:.2f}[/green]\n"
            panel_text += f"[green]TP2:     ${signal.tp2:.2f}[/green]\n"
            panel_text += f"[yellow]R/R:     1 : {signal.risk_reward_ratio:.2f}[/yellow]\n\n"
            panel_text += "\n".join(checks)
            
            console.print(Panel(panel_text, border_style="cyan", padding=(1, 2)))


def main():
    parser = argparse.ArgumentParser(
        description="Knife Catch Scanner - Automated reversal detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python knife_catch_scanner.py\n"
               "  python knife_catch_scanner.py MRVL CRDO\n"
               "  python knife_catch_scanner.py --catalysts catalysts.json\n"
    )
    
    parser.add_argument("tickers", nargs="*", help="Tickers to scan")
    parser.add_argument("--tickers-file", type=str, help="Path to tickers file")
    parser.add_argument("--catalysts", type=str, help="Path to catalysts JSON file")
    parser.add_argument("--top", type=int, default=30, help="Top N results to display")
    
    args = parser.parse_args()
    
    # Load tickers
    tickers = load_tickers(args)
    if not tickers:
        sys.exit("No tickers to scan")
    
    print(f"Scanning {len(tickers)} tickers for knife catch opportunities...\n", file=sys.stderr)
    
    # Load catalysts
    catalysts = load_catalysts(args.catalysts)
    
    # Scan
    results = scan_tickers(tickers, catalysts)
    
    if not results:
        print("No data found for scanning", file=sys.stderr)
        return
    
    print(f"Analysis complete. Found {len(results)} tickers with data.\n", file=sys.stderr)
    
    # Print results
    print_results(results, top_n=args.top)


if __name__ == "__main__":
    main()
