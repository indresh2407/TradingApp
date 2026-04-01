#!/usr/bin/env python3
"""
Debug Tomorrow's Intraday - Check what data we get and why signals aren't showing
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Test with key stocks
TEST_STOCKS = ["IDBI", "SBIN", "RELIANCE", "HDFCBANK", "TCS", "TATAMOTORS", "ICICIBANK", "PNB"]

def calculate_atr(high, low, close, period=10):
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean().iloc[-1]

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 50

print("=" * 70)
print("DEBUG: TOMORROW'S INTRADAY ANALYSIS")
print("=" * 70)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

total_api_success = 0
total_api_fail = 0

for symbol in TEST_STOCKS:
    yahoo_symbol = f"{symbol}.NS"
    print(f"\n{'='*70}")
    print(f"📊 {symbol}")
    print("-" * 70)
    
    try:
        ticker = yf.Ticker(yahoo_symbol)
        hist = ticker.history(period="1mo", interval="1d")
        
        if hist.empty:
            print(f"  ❌ API returned NO DATA")
            total_api_fail += 1
            continue
        
        if len(hist) < 10:
            print(f"  ⚠️ Only {len(hist)} days data (need 10+)")
            total_api_fail += 1
            continue
        
        total_api_success += 1
        print(f"  ✅ API returned {len(hist)} days of data")
        
        # Latest values
        ltp = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        today_open = hist['Open'].iloc[-1]
        today_high = hist['High'].iloc[-1]
        today_low = hist['Low'].iloc[-1]
        today_volume = hist['Volume'].iloc[-1]
        
        change = ltp - prev_close
        change_pct = (change / prev_close) * 100
        
        print(f"\n  📈 TODAY'S DATA:")
        print(f"     Open:   ₹{today_open:,.2f}")
        print(f"     High:   ₹{today_high:,.2f}")
        print(f"     Low:    ₹{today_low:,.2f}")
        print(f"     Close:  ₹{ltp:,.2f}")
        print(f"     Change: {change:+.2f} ({change_pct:+.2f}%)")
        print(f"     Volume: {today_volume:,.0f}")
        
        # Analysis
        day_range = today_high - today_low if today_high > today_low else 0.01
        close_position = (ltp - today_low) / day_range
        
        strong_close = close_position > 0.75
        weak_close = close_position < 0.25
        positive_candle = ltp > today_open
        negative_candle = ltp < today_open
        
        # ATR
        atr = calculate_atr(hist['High'], hist['Low'], hist['Close'], period=10)
        atr_pct = (atr / ltp) * 100
        
        # Volume
        avg_volume = hist['Volume'].tail(20).mean()
        volume_ratio = today_volume / avg_volume if avg_volume > 0 else 1
        volume_surge = volume_ratio > 1.5
        
        # RSI
        rsi = calculate_rsi(hist['Close'])
        
        # SMA
        sma_20 = hist['Close'].rolling(20).mean().iloc[-1]
        above_sma = ltp > sma_20
        
        # Breaking out
        prev_4d_high = hist['High'].tail(5).head(4).max()
        prev_4d_low = hist['Low'].tail(5).head(4).min()
        breaking_up = ltp > prev_4d_high
        breaking_down = ltp < prev_4d_low
        
        # Support/Resistance
        recent_low = hist['Low'].tail(10).min()
        recent_high = hist['High'].tail(10).max()
        at_support = (ltp - recent_low) / ltp * 100 < 2
        at_resistance = (recent_high - ltp) / ltp * 100 < 2
        
        print(f"\n  📊 ANALYSIS:")
        print(f"     Close Position: {close_position*100:.0f}% {'(STRONG ✅)' if strong_close else '(WEAK ⚠️)' if weak_close else ''}")
        print(f"     Candle: {'Green ⬆️' if positive_candle else 'Red ⬇️'}")
        print(f"     ATR%: {atr_pct:.2f}%")
        print(f"     Volume: {volume_ratio:.1f}x avg {'(SURGE ✅)' if volume_surge else ''}")
        print(f"     RSI: {rsi:.1f}")
        print(f"     vs SMA20: {'Above ⬆️' if above_sma else 'Below ⬇️'}")
        print(f"     4-Day Range: ₹{prev_4d_low:.2f} - ₹{prev_4d_high:.2f}")
        print(f"     Breaking Up: {'YES 🚀' if breaking_up else 'No'}")
        print(f"     At Support: {'YES 📍' if at_support else 'No'}")
        
        # SCORING
        long_score = 0
        short_score = 0
        long_triggers = []
        short_triggers = []
        
        # Long scoring
        if strong_close:
            long_score += 20
            long_triggers.append(f"Strong Close (+20)")
        if positive_candle:
            if at_support:
                long_score += 20
                long_triggers.append(f"Support Bounce (+20)")
        if breaking_up:
            long_score += 20
            long_triggers.append(f"Breaking Up! (+20)")
        if above_sma:
            long_score += 10
            long_triggers.append(f">SMA20 (+10)")
        if volume_surge:
            long_score += 10
            long_triggers.append(f"Volume {volume_ratio:.1f}x (+10)")
        if change_pct > 0.5:
            long_score += 10
            long_triggers.append(f"+{change_pct:.1f}% (+10)")
        if change_pct > 2:
            long_score += 10
            long_triggers.append(f"Big move! (+10)")
        if atr_pct > 2:
            long_score += 10
            long_triggers.append(f"High ATR (+10)")
        
        # Short scoring
        if weak_close:
            short_score += 20
            short_triggers.append(f"Weak Close (+20)")
        if negative_candle:
            if at_resistance:
                short_score += 20
                short_triggers.append(f"Resistance Reject (+20)")
        if breaking_down:
            short_score += 20
            short_triggers.append(f"Breaking Down! (+20)")
        if not above_sma:
            short_score += 10
            short_triggers.append(f"<SMA20 (+10)")
        if volume_surge and change_pct < 0:
            short_score += 10
            short_triggers.append(f"Volume {volume_ratio:.1f}x (+10)")
        if change_pct < -0.5:
            short_score += 10
            short_triggers.append(f"{change_pct:.1f}% (+10)")
        if change_pct < -2:
            short_score += 10
            short_triggers.append(f"Big drop! (+10)")
        if atr_pct > 2:
            short_score += 10
            short_triggers.append(f"High ATR (+10)")
        
        print(f"\n  📊 SCORING:")
        print(f"     LONG Score:  {long_score} (need >= 15)")
        if long_triggers:
            for t in long_triggers:
                print(f"       • {t}")
        print(f"     SHORT Score: {short_score} (need >= 15)")
        if short_triggers:
            for t in short_triggers:
                print(f"       • {t}")
        
        # Signal decision
        print(f"\n  🎯 SIGNAL DECISION:")
        if long_score >= 15 and long_score > short_score:
            print(f"     ✅ LONG SIGNAL - Score: {long_score}")
        elif short_score >= 15 and short_score > long_score:
            print(f"     ✅ SHORT SIGNAL - Score: {short_score}")
        else:
            print(f"     ❌ NO SIGNAL")
            if long_score < 15 and short_score < 15:
                print(f"        Reason: Both scores below 15")
            elif long_score == short_score:
                print(f"        Reason: Equal scores (no clear direction)")
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        total_api_fail += 1

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"API Success: {total_api_success}/{len(TEST_STOCKS)}")
print(f"API Failures: {total_api_fail}/{len(TEST_STOCKS)}")

if total_api_fail > 0:
    print("\n⚠️  Some API calls failed. Possible causes:")
    print("    1. Network issue")
    print("    2. Yahoo Finance rate limiting")
    print("    3. Market closed (no fresh data)")

print("\n" + "=" * 70)
