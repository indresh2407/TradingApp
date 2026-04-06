"""
Explain exactly why indicators were NaN at each trade time
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

def main():
    print("=" * 80)
    print("WHY INDICATORS WERE NaN - DETAILED EXPLANATION")
    print("=" * 80)
    print()
    
    # Market opens at 9:15 AM
    # Each 5-minute candle: 9:15, 9:20, 9:25, 9:30, ...
    
    print("INDICATOR REQUIREMENTS:")
    print("-" * 40)
    print("  Supertrend: Needs 10 candles (period=10)")
    print("  ADX: Needs ~20 candles (di_length=10 + adx_smoothing=10)")
    print("  RSI: Needs 14 candles (period=14)")
    print()
    
    print("CANDLE COUNT BY TIME:")
    print("-" * 40)
    times = [
        ("9:15 AM", 1),
        ("9:20 AM", 2),
        ("9:25 AM", 3),
        ("9:30 AM", 4),
        ("9:35 AM", 5),
        ("9:40 AM", 6),
        ("9:45 AM", 7),
        ("9:50 AM", 8),
        ("9:55 AM", 9),
        ("10:00 AM", 10),
        ("10:05 AM", 11),
        ("10:10 AM", 12),
        ("10:15 AM", 13),
        ("10:20 AM", 14),
        ("10:25 AM", 15),
        ("10:30 AM", 16),
        ("10:35 AM", 17),
        ("10:40 AM", 18),
        ("10:45 AM", 19),
        ("10:50 AM", 20),
        ("10:55 AM", 21),
        ("11:00 AM", 22),
    ]
    
    for time, candles in times:
        st_status = "✅ Valid" if candles >= 10 else f"❌ NaN (need 10, have {candles})"
        adx_status = "✅ Valid" if candles >= 20 else f"❌ NaN (need ~20, have {candles})"
        print(f"  {time:10} | Candles: {candles:2} | ST: {st_status:30} | ADX: {adx_status}")
    
    print()
    print("=" * 80)
    print("YOUR TRADES - EXACT CANDLE COUNT")
    print("=" * 80)
    print()
    
    trades = [
        ("POLICYBZR", "9:27 AM", "SHORT", 3),
        ("UNIONBANK", "10:08 AM", "LONG", 11),
        ("KOTAKBANK", "10:47 AM", "SHORT", 19),
        ("TORNTPHARM", "11:25 AM", "SHORT", 26),
        ("HINDUNILVR", "11:40 AM", "SHORT", 29),
    ]
    
    for stock, time, direction, candles in trades:
        print(f"{stock} at {time} ({direction}):")
        print(f"  Candles available: {candles}")
        
        # Supertrend status
        if candles < 10:
            print(f"  Supertrend: ❌ NaN (needs 10 candles, only had {candles})")
        else:
            print(f"  Supertrend: ✅ Calculated ({candles} >= 10)")
        
        # ADX status
        if candles < 20:
            print(f"  ADX: ❌ NaN (needs ~20 candles, only had {candles})")
        else:
            print(f"  ADX: ✅ Calculated ({candles} >= 20)")
        
        print()
    
    print("=" * 80)
    print("ACTUAL DATA FROM TODAY")
    print("=" * 80)
    print()
    
    # Fetch actual data for verification
    stocks_to_check = [
        ("POLICYBZR.NS", "9:25", "9:30"),
        ("UNIONBANK.NS", "10:05", "10:10"),
        ("KOTAKBANK.NS", "10:45", "10:50"),
    ]
    
    for symbol, start_time, end_time in stocks_to_check:
        print(f"\n{symbol}:")
        print("-" * 40)
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="1d", interval="5m")
            
            # Get today's data
            today = datetime.now(IST).date()
            df_today = df[df.index.date == today]
            
            print(f"  Total candles today: {len(df_today)}")
            
            # Filter for the specific time
            time_df = df_today.between_time(start_time, end_time)
            
            if len(time_df) > 0:
                row = time_df.iloc[0]
                idx = df_today.index.get_loc(row.name)
                print(f"  At {start_time}: Candle index = {idx + 1} (1-based)")
                print(f"  Close price: ₹{row['Close']:.2f}")
                
                # Check if enough candles for indicators
                if idx + 1 < 10:
                    print(f"  Supertrend: ❌ Would be NaN ({idx + 1} < 10 candles)")
                else:
                    print(f"  Supertrend: ✅ Would be calculated")
                
                if idx + 1 < 20:
                    print(f"  ADX: ❌ Would be NaN ({idx + 1} < 20 candles)")
                else:
                    print(f"  ADX: ✅ Would be calculated")
        except Exception as e:
            print(f"  Error: {e}")
    
    print()
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("""
NaN means "Not a Number" - the indicator couldn't calculate because:

1. POLICYBZR at 9:27 AM (Candle #3):
   - Only 3 candles existed since market open
   - Supertrend needs 10 → NaN
   - ADX needs 20 → NaN
   
2. UNIONBANK at 10:08 AM (Candle #11):
   - 11 candles existed
   - Supertrend needs 10 → Just starting to calculate
   - ADX needs 20 → Still NaN
   
3. KOTAKBANK at 10:47 AM (Candle #19):
   - 19 candles existed
   - Supertrend needs 10 → Valid
   - ADX needs 20 → Just about to be valid

The FIX: Use TODAY's data only + require minimum 10 candles
This naturally delays signals until 10:05 AM when indicators are ready.
""")

if __name__ == "__main__":
    main()
