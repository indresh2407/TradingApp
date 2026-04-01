#!/usr/bin/env python3
"""
Debug script to check why Breakout Alert isn't showing any stocks
Run this locally: python debug_breakout.py
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

# Test stocks from NIFTY 50
TEST_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY",
    "TATAMOTORS", "SBIN", "ITC", "BHARTIARTL", "LT",
    "AXISBANK", "MARUTI", "TITAN", "BAJFINANCE", "WIPRO"
]

def get_yahoo_symbol(nse_symbol):
    return f"{nse_symbol}.NS"

def analyze_stock(symbol):
    """Analyze a single stock for breakout potential"""
    yahoo_symbol = get_yahoo_symbol(symbol)
    
    try:
        ticker = yf.Ticker(yahoo_symbol)
        hist = ticker.history(period="5d", interval="5m")
        
        if hist.empty:
            return {"symbol": symbol, "error": "No data", "score": 0}
        
        if len(hist) < 50:
            return {"symbol": symbol, "error": f"Only {len(hist)} candles", "score": 0}
        
        # Current values
        ltp = hist['Close'].iloc[-1]
        
        # Today's data
        today = datetime.now().date()
        if hist.index.tz is not None:
            today_data = hist[hist.index.date == today]
        else:
            today_data = hist.tail(75)
        
        if len(today_data) < 5:
            today_data = hist.tail(30)
        
        # Day OHLC
        if len(today_data) > 0:
            day_open = today_data['Open'].iloc[0]
            day_high = today_data['High'].max()
            day_low = today_data['Low'].min()
        else:
            day_open = hist['Open'].iloc[-30]
            day_high = hist['High'].tail(30).max()
            day_low = hist['Low'].tail(30).min()
        
        change_pct = ((ltp - day_open) / day_open) * 100
        
        # === SCORING ===
        score_breakdown = {}
        total_score = 0
        
        # 1. ATR Squeeze
        tr = hist['High'] - hist['Low']
        atr_20 = tr.rolling(20).mean().iloc[-1]
        atr_5 = tr.rolling(5).mean().iloc[-1]
        atr_squeeze = atr_5 < atr_20 * 0.9
        atr_score = 20 if atr_squeeze else 0
        score_breakdown['ATR Squeeze'] = f"{atr_score} (ATR5={atr_5:.2f}, ATR20={atr_20:.2f}, squeeze={atr_squeeze})"
        total_score += atr_score
        
        # 2. Volume Surge
        avg_volume = hist['Volume'].rolling(50).mean().iloc[-1]
        recent_volume = hist['Volume'].tail(5).mean()
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        volume_surge = volume_ratio > 1.2
        vol_score = min(20, int(volume_ratio * 10)) if volume_surge else 0
        score_breakdown['Volume Surge'] = f"{vol_score} (ratio={volume_ratio:.2f}x, surge={volume_surge})"
        total_score += vol_score
        
        # 3. VWAP Position (simplified)
        typical_price = (hist['High'] + hist['Low'] + hist['Close']) / 3
        vwap = (typical_price * hist['Volume']).cumsum() / hist['Volume'].cumsum()
        current_vwap = vwap.iloc[-1]
        vwap_distance = ((ltp - current_vwap) / current_vwap) * 100
        vwap_score = 15 if abs(vwap_distance) < 0.5 else 0
        if ltp > current_vwap:
            vwap_score += 10
        elif ltp < current_vwap:
            vwap_score += 10
        score_breakdown['VWAP'] = f"{vwap_score} (VWAP={current_vwap:.2f}, dist={vwap_distance:.2f}%)"
        total_score += vwap_score
        
        # 4. Near Key Levels
        near_day_high = ltp >= day_high * 0.99
        near_day_low = ltp <= day_low * 1.01
        level_score = 0
        direction = "NEUTRAL"
        if near_day_high:
            level_score = 25
            direction = "BULLISH"
        elif near_day_low:
            level_score = 25
            direction = "BEARISH"
        score_breakdown['Key Levels'] = f"{level_score} (near_high={near_day_high}, near_low={near_day_low})"
        total_score += level_score
        
        # 5. Supertrend (simplified)
        st_score = 12  # Give base score
        score_breakdown['Supertrend'] = f"{st_score} (simplified)"
        total_score += st_score
        
        # 6. Range Compression
        recent_range = (hist['High'].tail(5) - hist['Low'].tail(5)).mean()
        avg_range = (hist['High'] - hist['Low']).rolling(20).mean().iloc[-1]
        range_compression = recent_range < avg_range * 0.8
        range_score = 15 if range_compression else 0
        score_breakdown['Range Compression'] = f"{range_score} (recent={recent_range:.2f}, avg={avg_range:.2f}, compressed={range_compression})"
        total_score += range_score
        
        # 7. Momentum
        momentum_score = 0
        rsi_approx = 50  # Simplified
        if abs(change_pct) > 0.5:
            momentum_score += 5
        if volume_ratio > 1.1:
            momentum_score += 8
        score_breakdown['Momentum'] = f"{momentum_score} (change={change_pct:.2f}%)"
        total_score += momentum_score
        
        return {
            "symbol": symbol,
            "ltp": ltp,
            "day_high": day_high,
            "day_low": day_low,
            "change_pct": change_pct,
            "volume_ratio": volume_ratio,
            "total_score": total_score,
            "passes_threshold": total_score >= 25,
            "direction": direction,
            "breakdown": score_breakdown,
            "error": None
        }
        
    except Exception as e:
        return {"symbol": symbol, "error": str(e), "score": 0}


def main():
    print("=" * 60)
    print("BREAKOUT ALERT DEBUG - Analyzing stocks...")
    print("=" * 60)
    print()
    
    results = []
    passing = []
    
    for symbol in TEST_STOCKS:
        print(f"Analyzing {symbol}...", end=" ")
        result = analyze_stock(symbol)
        results.append(result)
        
        if result.get("error"):
            print(f"ERROR: {result['error']}")
        else:
            score = result['total_score']
            passes = "✅ PASSES" if result['passes_threshold'] else "❌ FAILS"
            print(f"Score: {score} {passes}")
            
            if result['passes_threshold']:
                passing.append(result)
    
    print()
    print("=" * 60)
    print("DETAILED BREAKDOWN")
    print("=" * 60)
    
    for result in results:
        if result.get("error"):
            continue
            
        print(f"\n{result['symbol']} - Score: {result['total_score']} ({'PASS' if result['passes_threshold'] else 'FAIL'})")
        print(f"  LTP: ₹{result['ltp']:.2f} | Day Range: ₹{result['day_low']:.2f} - ₹{result['day_high']:.2f}")
        print(f"  Change: {result['change_pct']:.2f}% | Volume: {result['volume_ratio']:.2f}x | Direction: {result['direction']}")
        print("  Score Breakdown:")
        for key, value in result['breakdown'].items():
            print(f"    - {key}: {value}")
    
    print()
    print("=" * 60)
    print(f"SUMMARY: {len(passing)}/{len(results)} stocks pass the threshold (>=25)")
    print("=" * 60)
    
    if passing:
        print("\nStocks that WOULD show in Breakout Alert:")
        for p in passing:
            print(f"  🚀 {p['symbol']} - Score: {p['total_score']} - {p['direction']}")
    else:
        print("\n⚠️  NO stocks currently pass the breakout threshold!")
        print("\nPossible reasons:")
        print("  1. Market is quiet/sideways - no breakout setups")
        print("  2. It's outside market hours - data may be stale")
        print("  3. Volume is low today")
        print("  4. Stocks are mid-range (not near day high/low)")
        
        # Show closest to passing
        valid_results = [r for r in results if not r.get("error")]
        if valid_results:
            sorted_results = sorted(valid_results, key=lambda x: x['total_score'], reverse=True)
            print("\nClosest to passing (top 5):")
            for r in sorted_results[:5]:
                needed = 25 - r['total_score']
                print(f"  {r['symbol']}: Score {r['total_score']} (needs {needed} more)")


if __name__ == "__main__":
    main()
