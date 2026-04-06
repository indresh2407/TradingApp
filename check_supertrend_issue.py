"""
Check why Supertrend is NaN for stocks today
"""

import yfinance as yf
import pandas as pd
import numpy as np

def calculate_supertrend(high, low, close, period=10, multiplier=3.0):
    """Same calculation as dashboard"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)
    
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)
    
    for i in range(period, len(close)):
        if basic_upper.iloc[i] < final_upper.iloc[i-1] or close.iloc[i-1] > final_upper.iloc[i-1]:
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i-1]
        
        if basic_lower.iloc[i] > final_lower.iloc[i-1] or close.iloc[i-1] < final_lower.iloc[i-1]:
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i-1]
        
        if i == period:
            if close.iloc[i] <= final_upper.iloc[i]:
                supertrend.iloc[i] = final_upper.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = final_lower.iloc[i]
                direction.iloc[i] = 1
        else:
            if supertrend.iloc[i-1] == final_upper.iloc[i-1]:
                if close.iloc[i] > final_upper.iloc[i]:
                    supertrend.iloc[i] = final_lower.iloc[i]
                    direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = final_upper.iloc[i]
                    direction.iloc[i] = -1
            else:
                if close.iloc[i] < final_lower.iloc[i]:
                    supertrend.iloc[i] = final_upper.iloc[i]
                    direction.iloc[i] = -1
                else:
                    supertrend.iloc[i] = final_lower.iloc[i]
                    direction.iloc[i] = 1
    
    return supertrend, direction

def main():
    print("=" * 80)
    print("SUPERTREND NaN INVESTIGATION")
    print("=" * 80)
    
    stocks = ["TORNTPHARM.NS", "KOTAKBANK.NS", "POLICYBZR.NS", "UNIONBANK.NS"]
    
    for symbol in stocks:
        print(f"\n{'=' * 40}")
        print(f"CHECKING: {symbol}")
        print("=" * 40)
        
        ticker = yf.Ticker(symbol)
        
        # Test 1: Only today's data (1d)
        print("\n1. With period='1d' (Today only):")
        df_1d = ticker.history(period="1d", interval="5m")
        print(f"   Candles fetched: {len(df_1d)}")
        
        if len(df_1d) > 10:
            st, direction = calculate_supertrend(df_1d['High'], df_1d['Low'], df_1d['Close'])
            non_nan = st.notna().sum()
            print(f"   Supertrend calculated: {non_nan} values (out of {len(df_1d)})")
            print(f"   First valid index: {st.first_valid_index()}")
            print(f"   Last value: {st.iloc[-1] if not pd.isna(st.iloc[-1]) else 'NaN'}")
        else:
            print("   Not enough data!")
        
        # Test 2: 5 days data (like dashboard)
        print("\n2. With period='5d' (5 days - like dashboard):")
        df_5d = ticker.history(period="5d", interval="5m")
        print(f"   Candles fetched: {len(df_5d)}")
        
        if len(df_5d) > 10:
            st, direction = calculate_supertrend(df_5d['High'], df_5d['Low'], df_5d['Close'])
            non_nan = st.notna().sum()
            print(f"   Supertrend calculated: {non_nan} values (out of {len(df_5d)})")
            print(f"   Last value: {st.iloc[-1]:.2f}" if not pd.isna(st.iloc[-1]) else "   Last value: NaN")
            print(f"   Last direction: {'BULLISH' if direction.iloc[-1] == 1 else 'BEARISH' if direction.iloc[-1] == -1 else 'N/A'}")
        
        # Check today's data within the 5d data
        if len(df_5d) > 50:
            # Get last 75 candles (roughly today)
            today_portion = df_5d.tail(75)
            st_today = st.tail(75)
            nan_count = st_today.isna().sum()
            print(f"\n   Today's portion ({len(today_portion)} candles):")
            print(f"   NaN values: {nan_count}")
            print(f"   Valid values: {len(today_portion) - nan_count}")
    
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("""
The issue is likely that:

1. Debug scripts used period='1d' (today only)
   - This gives ~26 candles by 11:25 AM
   - Supertrend needs 10 candles to start calculating
   - But the first 10 candles remain NaN
   
2. Dashboard uses period='5d' (5 days)
   - This gives 300+ candles
   - Supertrend starts calculating from candle 11
   - TODAY's candles should all have valid Supertrend
   
If Supertrend is STILL NaN in dashboard, there may be:
   - An exception being caught silently
   - A data format issue
   - A timezone/index issue
""")

if __name__ == "__main__":
    main()
