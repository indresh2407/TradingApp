#!/usr/bin/env python3
"""
Check if IDBI Bank would have triggered a breakout alert at any time today
Run: python check_idbi_breakout.py
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def analyze_idbi_breakout():
    print("=" * 70)
    print("IDBI BANK BREAKOUT ANALYSIS - Checking all candles today")
    print("=" * 70)
    
    # Fetch IDBI data
    symbol = "IDBI.NS"
    print(f"\nFetching data for {symbol}...")
    
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d", interval="5m")
    
    if hist.empty:
        print("ERROR: No data received!")
        return
    
    print(f"Total candles: {len(hist)}")
    print(f"Date range: {hist.index[0]} to {hist.index[-1]}")
    
    # Get today's data
    today = datetime.now().date()
    if hist.index.tz is not None:
        today_data = hist[hist.index.date == today]
    else:
        # Fallback - last trading day
        today_data = hist.tail(75)
    
    print(f"Today's candles: {len(today_data)}")
    
    if len(today_data) < 5:
        print("Not enough today data, using last 75 candles")
        today_data = hist.tail(75)
    
    # Day OHLC
    day_open = today_data['Open'].iloc[0]
    day_high = today_data['High'].max()
    day_low = today_data['Low'].min()
    current_ltp = today_data['Close'].iloc[-1]
    
    print(f"\n--- TODAY'S SUMMARY ---")
    print(f"Open:  ₹{day_open:.2f}")
    print(f"High:  ₹{day_high:.2f}")
    print(f"Low:   ₹{day_low:.2f}")
    print(f"LTP:   ₹{current_ltp:.2f}")
    print(f"Change: {((current_ltp - day_open) / day_open * 100):.2f}%")
    
    # Opening range (first 15 min = 3 candles)
    if len(today_data) >= 3:
        opening_high = today_data['High'].iloc[:3].max()
        opening_low = today_data['Low'].iloc[:3].min()
    else:
        opening_high = day_high
        opening_low = day_low
    
    print(f"\nOpening Range (first 15 min):")
    print(f"  High: ₹{opening_high:.2f}")
    print(f"  Low:  ₹{opening_low:.2f}")
    
    print("\n" + "=" * 70)
    print("CHECKING EACH CANDLE FOR BREAKOUT SIGNALS...")
    print("=" * 70)
    
    breakout_times = []
    
    # Iterate through each candle and calculate score
    for i in range(20, len(hist)):  # Need at least 20 candles for indicators
        candle_time = hist.index[i]
        ltp = hist['Close'].iloc[i]
        
        # Use data up to this candle
        hist_slice = hist.iloc[:i+1]
        
        # Calculate running day high/low up to this point (for today's candles)
        if hist.index.tz is not None:
            candle_date = candle_time.date()
            day_slice = hist_slice[hist_slice.index.date == candle_date]
        else:
            day_slice = hist_slice.tail(75)
        
        if len(day_slice) < 3:
            continue
            
        running_day_high = day_slice['High'].max()
        running_day_low = day_slice['Low'].min()
        running_day_open = day_slice['Open'].iloc[0]
        change_pct = ((ltp - running_day_open) / running_day_open) * 100
        
        # === CALCULATE BREAKOUT SCORE ===
        total_score = 0
        signals = []
        
        # 1. ATR Squeeze
        tr = hist_slice['High'] - hist_slice['Low']
        atr_20 = tr.rolling(20).mean().iloc[-1]
        atr_5 = tr.rolling(5).mean().iloc[-1]
        if atr_5 < atr_20 * 0.9:
            total_score += 20
            signals.append("ATR Squeeze")
        
        # 2. Volume Surge
        avg_volume = hist_slice['Volume'].rolling(50).mean().iloc[-1]
        recent_volume = hist_slice['Volume'].tail(5).mean()
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        if volume_ratio > 1.2:
            total_score += min(20, int(volume_ratio * 10))
            signals.append(f"Vol {volume_ratio:.1f}x")
        
        # 3. VWAP
        typical_price = (hist_slice['High'] + hist_slice['Low'] + hist_slice['Close']) / 3
        vwap = (typical_price * hist_slice['Volume']).cumsum() / hist_slice['Volume'].cumsum()
        current_vwap = vwap.iloc[-1]
        vwap_distance = ((ltp - current_vwap) / current_vwap) * 100
        if abs(vwap_distance) < 0.5:
            total_score += 15
            signals.append("Near VWAP")
        if ltp > current_vwap:
            total_score += 10
            signals.append(">VWAP")
        elif ltp < current_vwap:
            total_score += 10
            signals.append("<VWAP")
        
        # 4. Near Key Levels
        near_day_high = ltp >= running_day_high * 0.99
        near_day_low = ltp <= running_day_low * 1.01
        
        if near_day_high:
            total_score += 25
            signals.append("Day High!")
        elif near_day_low:
            total_score += 25
            signals.append("Day Low!")
        
        # Check opening range
        if len(day_slice) >= 3:
            orb_high = day_slice['High'].iloc[:3].max()
            orb_low = day_slice['Low'].iloc[:3].min()
            if ltp >= orb_high * 0.99 and not near_day_high:
                total_score += 15
                signals.append("ORB High")
            elif ltp <= orb_low * 1.01 and not near_day_low:
                total_score += 15
                signals.append("ORB Low")
        
        # 5. Supertrend (simplified)
        total_score += 12
        
        # 6. Range Compression
        recent_range = (hist_slice['High'].tail(5) - hist_slice['Low'].tail(5)).mean()
        avg_range = (hist_slice['High'] - hist_slice['Low']).rolling(20).mean().iloc[-1]
        if recent_range < avg_range * 0.8:
            total_score += 15
            signals.append("Tight Range")
        
        # 7. Momentum
        if abs(change_pct) > 0.5:
            total_score += 5
            signals.append(f"Move {change_pct:+.1f}%")
        if volume_ratio > 1.1:
            total_score += 8
        
        # Check if passes threshold
        if total_score >= 15:  # Current threshold
            breakout_times.append({
                "time": candle_time,
                "ltp": ltp,
                "score": total_score,
                "signals": signals,
                "change_pct": change_pct,
                "near_high": near_day_high,
                "near_low": near_day_low
            })
    
    print(f"\n--- RESULTS ---")
    print(f"Total candles analyzed: {len(hist) - 20}")
    print(f"Breakout signals found: {len(breakout_times)}")
    
    if breakout_times:
        print("\n🚀 BREAKOUT SIGNALS DETECTED:")
        print("-" * 70)
        
        # Group by significant score changes
        last_score = 0
        for b in breakout_times:
            # Only show when score is significantly different or key level hit
            if abs(b['score'] - last_score) >= 5 or b['near_high'] or b['near_low']:
                time_str = b['time'].strftime("%H:%M") if hasattr(b['time'], 'strftime') else str(b['time'])
                direction = "🟢 LONG" if b['near_high'] or b['change_pct'] > 0 else "🔴 SHORT"
                print(f"{time_str} | Score: {b['score']:3d} | ₹{b['ltp']:.2f} ({b['change_pct']:+.2f}%) | {direction}")
                print(f"         Signals: {', '.join(b['signals'][:5])}")
                last_score = b['score']
        
        # Show peak breakout
        peak = max(breakout_times, key=lambda x: x['score'])
        print(f"\n🔥 STRONGEST SIGNAL:")
        time_str = peak['time'].strftime("%H:%M") if hasattr(peak['time'], 'strftime') else str(peak['time'])
        print(f"   Time: {time_str}")
        print(f"   Score: {peak['score']}")
        print(f"   Price: ₹{peak['ltp']:.2f}")
        print(f"   Signals: {', '.join(peak['signals'])}")
    else:
        print("\n❌ NO BREAKOUT SIGNALS DETECTED")
        print("\nReasons could be:")
        print("  - Stock stayed in mid-range (not near high/low)")
        print("  - Low volume day")
        print("  - No volatility squeeze")
        print("  - Sideways movement")
        
        # Show what we'd need
        print(f"\n📊 Current Analysis:")
        print(f"  LTP vs Day High: {((current_ltp / day_high - 1) * 100):+.2f}% (need within 1% for signal)")
        print(f"  LTP vs Day Low: {((current_ltp / day_low - 1) * 100):+.2f}% (need within 1% for signal)")


if __name__ == "__main__":
    analyze_idbi_breakout()
