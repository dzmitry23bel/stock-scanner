#!/usr/bin/env bash

# KNIFE CATCH SCANNER - Quick Setup Guide
# ========================================

# 1. Ensure dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# 2. Test single run
echo ""
echo "Testing scanner with 5 tickers..."
.venv/bin/python knife_catch_scanner.py MRVL CRDO CGEM GOOGL MPWR

# 3. Run full scan
echo ""
echo "Running full scan on all 142 tickers (top 50)..."
.venv/bin/python knife_catch_scanner.py --top 50

# 4. (Optional) Set up daily automation on macOS
echo ""
echo "To set up automated daily scans at 4:10 PM ET (market close):"
echo ""
echo "  1. Edit com.user.knife-catch-scanner.plist if needed (adjust paths/times)"
echo "  2. Copy to launchd: cp com.user.knife-catch-scanner.plist ~/Library/LaunchAgents/"
echo "  3. Load it: launchctl load ~/Library/LaunchAgents/com.user.knife-catch-scanner.plist"
echo "  4. Check status: launchctl list | grep knife-catch"
echo "  5. View logs: tail -f scan_results/scanner.log"
echo ""
echo "To unload: launchctl unload ~/Library/LaunchAgents/com.user.knife-catch-scanner.plist"
echo ""

# 5. Show project structure
echo "Project Structure:"
echo "==================="
tree -L 2 -I '__pycache__|*.pyc|.venv'

echo ""
echo "✓ Setup complete! You're ready to scan for knife catch opportunities."
echo ""
echo "Next steps:"
echo "  1. Run: python knife_catch_scanner.py --top 50"
echo "  2. Review top candidates (score >= 75)"
echo "  3. Check entry/stop/TP levels for each"
echo "  4. Verify support on live charts before entering"
echo ""
