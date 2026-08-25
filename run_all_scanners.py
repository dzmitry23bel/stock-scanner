#!/usr/bin/env python3
"""Master Scanner - Unified runner for all three scanners.

Runs Knife Catch, Trend/Momentum, and Day Trading scanners in parallel,
consolidates results, identifies consensus signals (high-conviction setups),
and generates a comprehensive master report.

Usage:
    python run_all_scanners.py                      # Full report, top 50 each
    python run_all_scanners.py --top 30             # Top 30 for each
    python run_all_scanners.py --catalysts catalysts.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import defaultdict

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

DEFAULT_SCANNERS_DIR = Path(__file__).parent
DEFAULT_REPORT_DIR = DEFAULT_SCANNERS_DIR / "scan_results" / "master"


def format_level(value: Optional[float]) -> str:
    return "-" if value is None else f"${value:.2f}"


def write_history_report(all_signals: dict, consensus_signals: list, report_dir: Path) -> Path:
    """Write a dated Markdown report and JSON snapshot for later review."""
    generated = datetime.now().astimezone()
    timestamp = generated.strftime("%Y-%m-%d_%H-%M-%S_%Z")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"master_report_{timestamp}.md"
    json_path = report_dir / f"master_report_{timestamp}.json"

    lines = [
        "# Master Scanner Report",
        "",
        f"**Generated:** {generated.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "",
        "| Scanner | Ticker | Score | Signal | Entry | Stop | TP1 | TP2 |",
        "|---|---:|---:|---|---:|---:|---:|---:|",
    ]
    for scanner_name, signals in all_signals.items():
        for signal in signals:
            lines.append(
                f"| {scanner_name} | {signal['ticker']} | {signal['score']:.1f} | "
                f"{signal.get('signal', 'WATCH')} | {format_level(signal.get('entry'))} | "
                f"{format_level(signal.get('stop'))} | {format_level(signal.get('tp1'))} | "
                f"{format_level(signal.get('tp2'))} |"
            )

    lines.extend(["", "## Consensus Signals", ""])
    if consensus_signals:
        lines.extend([
            "| Ticker | Average Score | Scanners |",
            "|---|---:|---|",
        ])
        for ticker, scanners in consensus_signals:
            average = sum(item["score"] for item in scanners) / len(scanners)
            names = ", ".join(item["scanner"] for item in scanners)
            lines.append(f"| {ticker} | {average:.1f} | {names} |")
    else:
        lines.append("No consensus signals found.")

    report_path.write_text("\n".join(lines) + "\n")
    json_path.write_text(json.dumps({
        "generated_at": generated.isoformat(),
        "scanners": all_signals,
        "consensus": [
            {"ticker": ticker, "signals": scanners}
            for ticker, scanners in consensus_signals
        ],
    }, indent=2, ensure_ascii=False) + "\n")
    return report_path


def get_knife_catch_signals(top_n: int = 50, catalysts: Optional[str] = None) -> list[dict]:
    """Get knife catch signals using direct import."""
    try:
        from scanners.knife_catch_scanner import scan_tickers
        from scanners.common import load_tickers as load_tickers_kc, load_catalysts
        
        # Load tickers
        class Args:
            tickers = []
            tickers_file = None
        
        tickers = load_tickers_kc(Args())
        catalysts_dict = load_catalysts(catalysts) if catalysts else {}
        
        print("Scanning for knife catch opportunities...", file=sys.stderr)
        results = scan_tickers(tickers, catalysts_dict)
        
        # Convert to simple dicts
        signals = []
        for r in sorted(results, key=lambda x: x.score, reverse=True)[:top_n]:
            signals.append({
                'ticker': r.ticker,
                'score': r.score,
                'scanner': 'knife_catch',
                'signal': r.classification,
                'entry': r.entry_price,
                'stop': r.stop_loss,
                'tp1': r.tp1,
                'tp2': r.tp2,
            })
        
        return signals
    except Exception as e:
        print(f"Error in knife catch scanner: {e}", file=sys.stderr)
        return []


def get_trend_momentum_signals(top_n: int = 50, catalysts: Optional[str] = None) -> list[dict]:
    """Get trend/momentum signals using direct import."""
    try:
        from scanners.long_term_scanner import (
            load_tickers as load_tickers_tm,
            load_catalysts,
            analyze
        )
        
        class Args:
            tickers = []
            tickers_file = None
        
        tickers = load_tickers_tm(Args())
        catalysts_dict = load_catalysts(catalysts) if catalysts else {}
        
        print("Scanning for trend/momentum opportunities...", file=sys.stderr)
        
        scores = []
        for ticker in tickers[:100]:  # Sample for speed
            result = analyze(ticker, catalysts_dict.get(ticker))
            if result is None:
                continue
            
            scores.append({
                'ticker': ticker,
                'score': result.get('final_score', 0),
                'scanner': 'trend_momentum',
                'signal': result.get('situation', 'WATCH'),
                'entry': result.get('price'),
                'stop': result.get('price') - 2 * result['atr'] if result.get('atr') else None,
                'tp1': result.get('price') + 2 * result['atr'] if result.get('atr') else None,
                'tp2': result.get('price') + 3.5 * result['atr'] if result.get('atr') else None,
            })
        
        # Sort and limit
        signals = sorted(scores, key=lambda x: x['score'], reverse=True)[:top_n]
        return signals
    except Exception as e:
        print(f"Error in trend/momentum scanner: {e}", file=sys.stderr)
        return []


def get_day_trade_signals(top_n: int = 50, catalysts: Optional[str] = None) -> list[dict]:
    """Get day trade signals using direct import."""
    try:
        from scanners.short_term_scanner import (
            load_tickers,
            load_catalysts,
            analyze_day
        )
        
        class Args:
            tickers = []
            tickers_file = None
        
        tickers = load_tickers(Args())
        catalysts_dict = load_catalysts(catalysts) if catalysts else {}
        
        print("Scanning for day trading opportunities...", file=sys.stderr)
        
        scores = []
        for ticker in tickers[:100]:  # Sample for speed
            result = analyze_day(ticker, catalysts_dict.get(ticker))
            if result is None:
                continue
            
            scores.append({
                'ticker': ticker,
                'score': result.get('day_score', 0),
                'scanner': 'day_trade',
                'signal': result.get('direction', 'WAIT'),
                'entry': result.get('price'),
                'stop': None,
                'tp1': None,
                'tp2': None,
            })

            from scanners.short_term_scanner import build_trade_plan
            plan = build_trade_plan(result)
            if plan:
                scores[-1].update({
                    'entry': (plan['entry_low'] + plan['entry_high']) / 2,
                    'stop': plan['stop'],
                    'tp1': plan['tp1'],
                    'tp2': plan['tp2'],
                })
        
        # Sort and limit
        signals = sorted(scores, key=lambda x: x['score'], reverse=True)[:top_n]
        return signals
    except Exception as e:
        print(f"Error in day trade scanner: {e}", file=sys.stderr)
        return []


def identify_consensus_signals(all_signals: dict) -> list[tuple]:
    """Identify tickers that appear in multiple scanners (high conviction)."""
    consensus = defaultdict(list)
    
    for scanner_type, signals in all_signals.items():
        for signal in signals:
            ticker = signal['ticker']
            consensus[ticker].append({
                'scanner': scanner_type,
                'score': signal['score']
            })
    
    # Filter to only those appearing in 2+ scanners
    multi_scanner_hits = {
        ticker: scanners 
        for ticker, scanners in consensus.items() 
        if len(scanners) >= 2
    }
    
    # Sort by average score
    sorted_consensus = sorted(
        multi_scanner_hits.items(),
        key=lambda x: sum(s['score'] for s in x[1]) / len(x[1]),
        reverse=True
    )
    
    return sorted_consensus


def print_results(all_signals: dict, consensus_signals: list) -> None:
    """Print results in formatted output."""
    
    if HAS_RICH:
        console = Console()
        
        # Title
        title = Text("MASTER SCANNER REPORT", style="bold magenta")
        subtitle = Text(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="cyan")
        console.print(Panel(title, subtitle=subtitle, border_style="magenta"))
        console.print("")
        
        # Knife Catch
        if all_signals.get("knife_catch"):
            console.print("[bold yellow]🎯 KNIFE CATCH SCANNER[/bold yellow] (Reversal - 1-5 days)")
            table = Table(show_header=True, header_style="bold")
            table.add_column("Ticker", style="cyan")
            table.add_column("Score", justify="right")
            table.add_column("Signal")
            table.add_column("Entry")
            table.add_column("Stop")
            table.add_column("TP1")
            table.add_column("TP2")
            
            for signal in all_signals["knife_catch"][:15]:
                table.add_row(signal['ticker'], f"{signal['score']:.1f}", signal.get('signal', '-'), format_level(signal.get('entry')), format_level(signal.get('stop')), format_level(signal.get('tp1')), format_level(signal.get('tp2')))
            
            console.print(table)
        else:
            console.print("[dim]No signals[/dim]")
        console.print("")
        
        # Trend/Momentum
        if all_signals.get("trend_momentum"):
            console.print("[bold green]📈 TREND/MOMENTUM SCANNER[/bold green] (Growth - 5-30 days)")
            table = Table(show_header=True, header_style="bold")
            table.add_column("Ticker", style="cyan")
            table.add_column("Score", justify="right")
            table.add_column("Signal")
            table.add_column("Entry")
            table.add_column("Stop")
            table.add_column("TP1")
            table.add_column("TP2")
            
            for signal in all_signals["trend_momentum"][:15]:
                table.add_row(signal['ticker'], f"{signal['score']:.1f}", signal.get('signal', '-'), format_level(signal.get('entry')), format_level(signal.get('stop')), format_level(signal.get('tp1')), format_level(signal.get('tp2')))
            
            console.print(table)
        else:
            console.print("[dim]No signals[/dim]")
        console.print("")
        
        # Day Trading
        if all_signals.get("day_trade"):
            console.print("[bold cyan]⚡ DAY TRADING SCANNER[/bold cyan] (Leveraged - 1-5 days)")
            table = Table(show_header=True, header_style="bold")
            table.add_column("Ticker", style="cyan")
            table.add_column("Score", justify="right")
            table.add_column("Signal")
            table.add_column("Entry")
            table.add_column("Stop")
            table.add_column("TP1")
            table.add_column("TP2")
            
            for signal in all_signals["day_trade"][:15]:
                table.add_row(signal['ticker'], f"{signal['score']:.1f}", signal.get('signal', '-'), format_level(signal.get('entry')), format_level(signal.get('stop')), format_level(signal.get('tp1')), format_level(signal.get('tp2')))
            
            console.print(table)
        else:
            console.print("[dim]No signals[/dim]")
        console.print("")
        
        # Consensus
        console.print("[bold red]🔥 HIGH CONVICTION SIGNALS[/bold red] (2+ scanners)")
        if consensus_signals:
            table = Table(show_header=True, header_style="bold red")
            table.add_column("Ticker", style="yellow")
            table.add_column("Avg Score", justify="right")
            table.add_column("Scanners", width=50)
            
            for ticker, scanners in consensus_signals[:20]:
                avg_score = sum(s['score'] for s in scanners) / len(scanners)
                scanners_str = " + ".join(
                    f"{s['scanner'][:6]} ({s['score']:.0f})"
                    for s in sorted(scanners, key=lambda x: x['score'], reverse=True)
                )
                table.add_row(ticker, f"{avg_score:.1f}", scanners_str)
            
            console.print(table)
        else:
            console.print("[dim]None found[/dim]")
        console.print("")
        
        footer = Text("Tip: Tickers appearing in 2+ scanners have higher conviction", style="dim")
        console.print(Panel(footer, border_style="dim"))
    else:
        # Plain text output
        print("\n" + "=" * 100)
        print("MASTER SCANNER REPORT")
        print("=" * 100)
        print("")
        
        if all_signals.get("knife_catch"):
            print("🎯 KNIFE CATCH (Reversal)")
            for s in all_signals["knife_catch"][:10]:
                print(f"  {s['ticker']:<8} {s['score']:>6.1f}")
            print("")
        
        if all_signals.get("trend_momentum"):
            print("📈 TREND/MOMENTUM (Growth)")
            for s in all_signals["trend_momentum"][:10]:
                print(f"  {s['ticker']:<8} {s['score']:>6.1f}")
            print("")
        
        if all_signals.get("day_trade"):
            print("⚡ DAY TRADING (Leveraged)")
            for s in all_signals["day_trade"][:10]:
                print(f"  {s['ticker']:<8} {s['score']:>6.1f}")
            print("")
        
        if consensus_signals:
            print("🔥 HIGH CONVICTION")
            for ticker, scanners in consensus_signals[:10]:
                avg = sum(s['score'] for s in scanners) / len(scanners)
                print(f"  {ticker:<8} {avg:>6.1f}")


def main():
    parser = argparse.ArgumentParser(
        description="Master Scanner - All three scanners unified",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  python run_all_scanners.py\n  python run_all_scanners.py --top 30\n"
    )
    
    parser.add_argument("--top", type=int, default=50, help="Top N results per scanner")
    parser.add_argument("--catalysts", type=str, help="Path to catalysts JSON file")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR, help="Directory for dated Markdown and JSON reports")
    
    args = parser.parse_args()
    
    print(f"\nMaster Scanner - Top {args.top} from each strategy\n", file=sys.stderr)
    
    # Get signals from all three
    all_signals = {
        "knife_catch": get_knife_catch_signals(args.top, args.catalysts),
        "trend_momentum": get_trend_momentum_signals(args.top, args.catalysts),
        "day_trade": get_day_trade_signals(args.top, args.catalysts),
    }
    
    # Get consensus
    consensus_signals = identify_consensus_signals(all_signals)
    
    # Print
    print_results(all_signals, consensus_signals)
    report_path = write_history_report(all_signals, consensus_signals, args.report_dir)
    print(f"Report saved to: {report_path}", file=sys.stderr)
    
    # Summary
    print(f"\n✓ Complete! ({len(all_signals['knife_catch'])} KC + {len(all_signals['trend_momentum'])} TM + {len(all_signals['day_trade'])} DT + {len(consensus_signals)} consensus)\n", file=sys.stderr)


if __name__ == "__main__":
    main()
