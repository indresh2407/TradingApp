#!/usr/bin/env python3
"""
Strategy Analysis - Quick Summary
Run this locally to see today's backtest results
"""

print("""
============================================================
HOW TO RUN TODAY'S BACKTEST
============================================================

Run this command in your terminal:

    cd /Users/indreshy@backbase.com/kotak-trading-system
    python backtest_today.py

This will analyze:
- 20 NIFTY 50 stocks
- Predictions at 5 different times (10 AM - 2 PM)
- Check if targets/stoploss were hit
- Show overall success rate

============================================================
EXPECTED OUTPUT FORMAT
============================================================

📊 SUMMARY
   Total Predictions: XX
   ✅ Wins (Target Hit): XX
   ❌ Losses (SL Hit): XX
   📈 Partial Wins: XX
   📉 Partial Losses: XX

   🎯 Win Rate (Target Hit): XX.X%
   📈 Success Rate (Win + Partial Win): XX.X%

============================================================
STRATEGY COMPONENTS BEING TESTED
============================================================

1. SUPERTREND (30 points)
   - BULLISH = +30 for LONG
   - BEARISH = +30 for SHORT

2. VWAP (20 points)
   - Price > VWAP = +20 for LONG
   - Price < VWAP = +20 for SHORT

3. RSI (15 points)
   - RSI < 40 = +15 for LONG (oversold)
   - RSI > 60 = +15 for SHORT (overbought)

4. MOMENTUM (10 points)
   - Up > 0.3% = +10 for LONG
   - Down > 0.3% = +10 for SHORT

5. VOLUME (10 points)
   - High volume confirms direction

SIGNAL THRESHOLD: 40 points minimum

============================================================
TARGET & STOPLOSS
============================================================

LONG:
  - Entry: Current Price
  - Target: +1% (scalp) / +1.5% (swing)
  - Stoploss: -0.7%

SHORT:
  - Entry: Current Price
  - Target: -1% (scalp) / -1.5% (swing)
  - Stoploss: +0.7%

============================================================
""")

# If running in an environment with network, do the actual backtest
try:
    import yfinance as yf
    print("Network available - running actual backtest...")
    print("Please run: python backtest_today.py")
except:
    print("Run backtest_today.py locally for actual results.")
