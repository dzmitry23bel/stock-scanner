#!/usr/bin/env python3
"""Master Scanner - Unified runner for all three scanners.

Runs Knife Catch, Trend/Momentum, and Day Trading scanners in parallel,
consolidates results, identifies consensus signals (high-conviction setups),
and generates a comprehensive master report.

Usage:
    python scripts/run_all_scanners.py                      # Full report, top 50 each
    python scripts/run_all_scanners.py --top 30             # Top 30 for each
    python scripts/run_all_scanners.py --catalysts catalysts.json
"""
from __future__ import annotations

import argparse
import html
import json
import os
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

# Add project root to path for package imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

DEFAULT_SCANNERS_DIR = PROJECT_ROOT
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports" / "master"


def format_level(value: Optional[float]) -> str:
    return "-" if value is None else f"${value:.2f}"


def visible_levels(signal: dict) -> dict:
    """Keep only Entry for non-actionable signals."""
    signal_name = signal.get("signal")
    wait_signal = signal_name == "🟡 WAIT" or signal_name == "WAIT"
    watch_signal = signal.get("scanner") == "trend_momentum" and signal_name == "WATCH"
    if wait_signal or watch_signal:
        return {"entry": signal.get("entry"), "stop": None, "tp1": None, "tp2": None}
    return signal


ACTIVE_SIGNALS = {
    "🟢 STRONG KNIFE CATCH",
    "🟢 LONG CANDIDATE",
    "BUY DIP",
    "MOMENTUM BUY",
    "LONG",
    "SHORT",
}


def active_signals(all_signals: dict) -> dict:
    """Return only actionable signals for the compact HTML report."""
    return {
        scanner: [signal for signal in signals if signal.get("signal") in ACTIVE_SIGNALS]
        for scanner, signals in all_signals.items()
    }


def write_html_report(all_signals: dict, report_dir: Path) -> Path:
    """Write a standalone, browser-friendly report with actionable signals only."""
    generated = datetime.now().astimezone()
    timestamp = generated.strftime("%Y-%m-%d_%H-%M-%S_%Z")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"master_report_{timestamp}.html"
    actionable = active_signals(all_signals)
    total = sum(len(signals) for signals in actionable.values())

    sections = []
    labels = {
        "knife_catch": ("Knife Catch", "Reversal setups", "gold"),
        "trend_momentum": ("Trend / Momentum", "Growth setups", "green"),
        "day_trade": ("Day Trading", "Short-term setups", "blue"),
    }
    for scanner, signals in actionable.items():
        title, subtitle, color = labels.get(scanner, (scanner, "", "green"))
        rows = []
        for signal in signals:
            levels = visible_levels(signal)
            rows.append(
                "<tr>"
                f"<td class=\"ticker\">{html.escape(str(signal['ticker']))}</td>"
                f"<td><span class=\"signal {color}\">{html.escape(str(signal.get('signal', '-')))}</span></td>"
                f"<td class=\"score\">{signal['score']:.1f}</td>"
                f"<td>{html.escape(format_level(levels.get('entry')))}</td>"
                f"<td>{html.escape(format_level(levels.get('stop')))}</td>"
                f"<td>{html.escape(format_level(levels.get('tp1')))}</td>"
                f"<td>{html.escape(format_level(levels.get('tp2')))}</td>"
                "</tr>"
            )
        body = "".join(rows) or '<tr><td class="empty" colspan="7">No active signals</td></tr>'
        sections.append(
            f'<section class="scanner {color}"><div class="section-heading"><div><h2>{title}</h2><p>{subtitle}</p></div><b>{len(signals):02d}</b></div>'
            '<div class="table-wrap"><table><thead><tr><th>Ticker</th><th>Signal</th><th>Score</th><th>Entry</th><th>Stop</th><th>TP1</th><th>TP2</th></tr></thead>'
            f"<tbody>{body}</tbody></table></div></section>"
        )

    document = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Master Scanner | {generated.strftime('%Y-%m-%d')}</title>
<style>
:root {{ color-scheme: dark; --bg:#101315; --panel:#181d20; --line:#2b3438; --muted:#93a0a5; --text:#eef3f1; --gold:#e4b85e; --green:#70d19a; --blue:#73b7e8; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:radial-gradient(circle at 85% -10%,#233b35 0,transparent 34%),var(--bg); color:var(--text); font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
.shell {{ max-width:1240px; margin:auto; padding:48px 24px 64px; }} .eyebrow {{ color:var(--muted); letter-spacing:.14em; text-transform:uppercase; font-size:12px; }}
h1 {{ margin:8px 0 4px; font-size:clamp(30px,5vw,56px); line-height:1; letter-spacing:-.02em; }} .date {{ color:var(--muted); }}
.summary {{ display:flex; gap:12px; flex-wrap:wrap; margin:30px 0; }} .metric {{ background:rgba(24,29,32,.86); border:1px solid var(--line); border-radius:10px; padding:14px 18px; min-width:150px; }} .metric strong {{ display:block; font-size:28px; }} .metric span {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
.scanner {{ background:rgba(24,29,32,.88); border:1px solid var(--line); border-top:3px solid var(--green); border-radius:10px; margin:18px 0; overflow:hidden; }} .scanner.gold {{ border-top-color:var(--gold); }} .scanner.blue {{ border-top-color:var(--blue); }}
.section-heading {{ display:flex; align-items:center; justify-content:space-between; padding:20px 22px 15px; }} h2 {{ margin:0; font-size:21px; }} .section-heading p {{ margin:3px 0 0; color:var(--muted); }} .section-heading b {{ color:var(--muted); font-size:22px; }}
.table-wrap {{ overflow-x:auto; }} table {{ width:100%; border-collapse:collapse; min-width:700px; }} th,td {{ padding:13px 16px; border-top:1px solid var(--line); text-align:right; white-space:nowrap; }} th:first-child,td:first-child,th:nth-child(2),td:nth-child(2) {{ text-align:left; }} th {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }} .ticker {{ font-weight:700; letter-spacing:.04em; }} .score {{ font-weight:700; }} .signal {{ display:inline-block; border:1px solid currentColor; border-radius:999px; padding:3px 9px; font-size:12px; }} .signal.gold {{ color:var(--gold); }} .signal.green {{ color:var(--green); }} .signal.blue {{ color:var(--blue); }} .empty {{ color:var(--muted); text-align:center; padding:28px; }} footer {{ color:var(--muted); font-size:12px; margin-top:28px; }}
@media(max-width:600px) {{ .shell {{ padding:30px 14px 45px; }} .metric {{ flex:1; min-width:120px; }} th,td {{ padding:11px 10px; }} }}
</style></head><body><main class="shell">
<div class="eyebrow">Actionable market setups</div><h1>Master Scanner</h1><div class="date">{generated.strftime('%A, %B %d, %Y · %H:%M:%S %Z')}</div>
<div class="summary"><div class="metric"><strong>{total}</strong><span>Active signals</span></div><div class="metric"><strong>{len(actionable['knife_catch'])}</strong><span>Reversal</span></div><div class="metric"><strong>{len(actionable['trend_momentum'])}</strong><span>Growth</span></div><div class="metric"><strong>{len(actionable['day_trade'])}</strong><span>Short term</span></div></div>
{''.join(sections)}<footer>WAIT, WATCH, and AVOID results are intentionally excluded. Verify live price, liquidity, volume, and risk before trading.</footer>
</main></body></html>'''
    report_path.write_text(document)
    return report_path


def write_history_report(all_signals: dict, report_dir: Path) -> Path:
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
            levels = visible_levels(signal)
            lines.append(
                f"| {scanner_name} | {signal['ticker']} | {signal['score']:.1f} | "
                f"{signal.get('signal', 'WATCH')} | {format_level(levels.get('entry'))} | "
                f"{format_level(levels.get('stop'))} | {format_level(levels.get('tp1'))} | "
                f"{format_level(levels.get('tp2'))} |"
            )

    report_path.write_text("\n".join(lines) + "\n")
    json_path.write_text(json.dumps({
        "generated_at": generated.isoformat(),
        "scanners": {
            scanner: [
                {**signal, **visible_levels(signal)}
                for signal in signals
            ]
            for scanner, signals in all_signals.items()
        },
    }, indent=2, ensure_ascii=False) + "\n")
    return report_path


def render_pdf_report(html_path: Path) -> Path:
    """Render the HTML report to a PDF file alongside it (for email clients that mangle HTML bodies)."""
    from weasyprint import HTML

    pdf_path = html_path.with_suffix(".pdf")
    HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    return pdf_path


def send_email_report(report_path: Path, all_signals: dict) -> None:
    """Email the HTML and PDF report as attachments via Gmail SMTP using env-provided credentials."""
    sender = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("REPORT_RECIPIENT") or sender

    if not sender or not app_password or not recipient:
        print(
            "Email requested (--email) but GMAIL_ADDRESS/GMAIL_APP_PASSWORD "
            "(and optionally REPORT_RECIPIENT) are not set. Aborting send.",
            file=sys.stderr,
        )
        sys.exit(1)

    actionable = active_signals(all_signals)
    total = sum(len(signals) for signals in actionable.values())
    summary_lines = [f"Master Scanner Report - {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}", ""]
    summary_lines.append(f"Active signals: {total}")
    for scanner, signals in actionable.items():
        summary_lines.append(f"  {scanner}: {len(signals)}")
    summary_lines.append("")
    summary_lines.append("Full report attached (HTML and PDF).")

    pdf_path = render_pdf_report(report_path)

    message = EmailMessage()
    message["Subject"] = f"Master Scanner Report - {total} active signals"
    message["From"] = sender
    message["To"] = recipient
    message.set_content("\n".join(summary_lines))
    message.add_attachment(
        report_path.read_bytes(),
        maintype="text",
        subtype="html",
        filename=report_path.name,
    )
    message.add_attachment(
        pdf_path.read_bytes(),
        maintype="application",
        subtype="pdf",
        filename=pdf_path.name,
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, app_password)
        smtp.send_message(message)
    print(f"Emailed report to {recipient}", file=sys.stderr)


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
                'stop': r.stop_loss if r.classification not in ('🟡 WAIT', 'WAIT') else None,
                'tp1': r.tp1 if r.classification not in ('🟡 WAIT', 'WAIT') else None,
                'tp2': r.tp2 if r.classification not in ('🟡 WAIT', 'WAIT') else None,
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
                'stop': result.get('price') - 2 * result['atr'] if result.get('atr') and result.get('situation') != 'WAIT' else None,
                'tp1': result.get('price') + 2 * result['atr'] if result.get('atr') and result.get('situation') != 'WAIT' else None,
                'tp2': result.get('price') + 3.5 * result['atr'] if result.get('atr') and result.get('situation') != 'WAIT' else None,
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


def print_results(all_signals: dict) -> None:
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
                levels = visible_levels(signal)
                table.add_row(signal['ticker'], f"{signal['score']:.1f}", signal.get('signal', '-'), format_level(levels.get('entry')), format_level(levels.get('stop')), format_level(levels.get('tp1')), format_level(levels.get('tp2')))
            
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
                levels = visible_levels(signal)
                table.add_row(signal['ticker'], f"{signal['score']:.1f}", signal.get('signal', '-'), format_level(levels.get('entry')), format_level(levels.get('stop')), format_level(levels.get('tp1')), format_level(levels.get('tp2')))
            
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
        


def main():
    parser = argparse.ArgumentParser(
        description="Master Scanner - All three scanners unified",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  python scripts/run_all_scanners.py\n  python scripts/run_all_scanners.py --top 30\n"
    )
    
    parser.add_argument("--top", type=int, default=50, help="Top N results per scanner")
    parser.add_argument("--catalysts", type=str, help="Path to catalysts JSON file")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR, help="Directory for dated Markdown and JSON reports")
    parser.add_argument("--email", action="store_true", help="Email the HTML report via Gmail SMTP (needs GMAIL_ADDRESS/GMAIL_APP_PASSWORD env vars)")
    
    args = parser.parse_args()
    
    print(f"\nMaster Scanner - Top {args.top} from each strategy\n", file=sys.stderr)
    
    # Get signals from all three
    all_signals = {
        "knife_catch": get_knife_catch_signals(args.top, args.catalysts),
        "trend_momentum": get_trend_momentum_signals(args.top, args.catalysts),
        "day_trade": get_day_trade_signals(args.top, args.catalysts),
    }
    
    # Print
    print_results(all_signals)
    report_path = write_history_report(all_signals, args.report_dir)
    html_path = write_html_report(all_signals, args.report_dir)
    print(f"Report saved to: {report_path}", file=sys.stderr)
    print(f"HTML report saved to: {html_path}", file=sys.stderr)

    if args.email:
        send_email_report(html_path, all_signals)
    
    # Summary
    print(f"\n✓ Complete! ({len(all_signals['knife_catch'])} KC + {len(all_signals['trend_momentum'])} TM + {len(all_signals['day_trade'])} DT)\n", file=sys.stderr)


if __name__ == "__main__":
    main()
