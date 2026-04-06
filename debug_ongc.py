"""
Debug ONGC SHORT Signal at 12:41 PM
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

def calculate_supertrend(high, low, close, period=10, multiplier=3.0):
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

def calculate_vwap(df):
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    return vwap

def calculate_adx(df, di_length=10, adx_smoothing=10):
    high, low, close = df['High'], df['Low'], df['Close']
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(window=di_length).mean()
    plus_di = 100 * (plus_dm.rolling(window=di_length).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=di_length).mean() / atr)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=adx_smoothing).mean()
    return adx, plus_di, minus_di

def main():
    print("=" * 80)
    print("ONGC SHORT SIGNAL ANALYSIS - 12:41 PM")
    print("=" * 80)
    print()
    
    # User's trade
    entry_price = 281.5
    exit_price = 282.31
    loss = exit_price - entry_price
    loss_pct = (loss / entry_price) * 100
    
    print(f"YOUR TRADE:")
    print(f"  SHORT Entry: ₹{entry_price} at 12:41 PM")
    print(f"  Exit (Loss): ₹{exit_price} at 1:05 PM")
    print(f"  Loss: ₹{loss:.2f} ({loss_pct:.2f}%) ❌")
    print(f"  Hold time: 24 minutes")
    print()
    
    # Fetch data
    ticker = yf.Ticker("ONGC.NS")
    df_5m = ticker.history(period="1d", interval="5m")
    
    if len(df_5m) < 20:
        print("ERROR: Not enough data")
        return
    
    # Get today's data only
    today = datetime.now(IST).date()
    df_today = df_5m[df_5m.index.date == today].copy()
    
    print(f"ONGC today: {len(df_today)} candles")
    print(f"Price range: ₹{df_today['Close'].min():.2f} - ₹{df_today['Close'].max():.2f}")
    print()
    
    # At 12:41 PM, candle count from 9:15 AM
    candle_count = 41  # Approximately
    print(f"At 12:41 PM: ~{candle_count} candles available")
    print(f"  Supertrend: ✅ Should be valid (need 10)")
    print(f"  ADX: ✅ Should be valid (need 20)")
    print()
    
    # Calculate indicators on TODAY's data
    df_today['VWAP'] = calculate_vwap(df_today)
    df_today['ST'], df_today['ST_Dir'] = calculate_supertrend(
        df_today['High'], df_today['Low'], df_today['Close']
    )
    df_today['ADX'], df_today['Plus_DI'], df_today['Minus_DI'] = calculate_adx(df_today)
    
    print("=" * 80)
    print("5-MINUTE DATA (12:30 PM - 1:15 PM) - TODAY's DATA ONLY")
    print("=" * 80)
    print()
    
    try:
        analysis_df = df_today.between_time('12:30', '13:15')
    except:
        analysis_df = df_today.tail(15)
    
    print(f"{'Time':<12} {'Close':>10} {'VWAP':>10} {'ST':>10} {'ST Dir':>8} {'ADX':>8} {'+DI':>8} {'-DI':>8}")
    print("-" * 85)
    
    for idx, row in analysis_df.iterrows():
        try:
            time_str = idx.strftime('%H:%M')
        except:
            time_str = str(idx)[:5]
        
        st_dir = "BULL" if row['ST_Dir'] == 1 else "BEAR" if row['ST_Dir'] == -1 else "N/A"
        
        highlight = ""
        if "12:40" <= time_str <= "12:45":
            highlight = " <-- ENTRY"
        elif "13:00" <= time_str <= "13:10":
            highlight = " <-- EXIT"
        
        adx_val = f"{row['ADX']:.1f}" if not pd.isna(row['ADX']) else "nan"
        plus_di = f"{row['Plus_DI']:.1f}" if not pd.isna(row['Plus_DI']) else "nan"
        minus_di = f"{row['Minus_DI']:.1f}" if not pd.isna(row['Minus_DI']) else "nan"
        st_val = f"{row['ST']:.2f}" if not pd.isna(row['ST']) else "nan"
        
        print(f"{time_str:<12} {row['Close']:>10.2f} {row['VWAP']:>10.2f} {st_val:>10} {st_dir:>8} {adx_val:>8} {plus_di:>8} {minus_di:>8}{highlight}")
    
    print()
    print("=" * 80)
    print("ANALYSIS AT ENTRY TIME (~12:41 PM)")
    print("=" * 80)
    
    try:
        entry_candles = df_today.between_time('12:40', '12:45')
        if len(entry_candles) > 0:
            entry_candle = entry_candles.iloc[0]
            
            print()
            print(f"AT SIGNAL TIME (~12:40):")
            print(f"  Close: ₹{entry_candle['Close']:.2f}")
            print(f"  VWAP:  ₹{entry_candle['VWAP']:.2f}")
            
            st_dir_text = "BULLISH" if entry_candle['ST_Dir'] == 1 else "BEARISH" if entry_candle['ST_Dir'] == -1 else "N/A"
            st_val = entry_candle['ST'] if not pd.isna(entry_candle['ST']) else 0
            st_is_nan = pd.isna(entry_candle['ST'])
            print(f"  Supertrend: ₹{st_val:.2f} ({st_dir_text}) {'⚠️ NaN!' if st_is_nan else ''}")
            
            adx = entry_candle['ADX'] if not pd.isna(entry_candle['ADX']) else 0
            adx_is_nan = pd.isna(entry_candle['ADX'])
            plus_di = entry_candle['Plus_DI'] if not pd.isna(entry_candle['Plus_DI']) else 0
            minus_di = entry_candle['Minus_DI'] if not pd.isna(entry_candle['Minus_DI']) else 0
            
            print(f"  ADX: {adx:.1f} {'⚠️ NaN!' if adx_is_nan else ''}")
            print(f"  +DI: {plus_di:.1f}, -DI: {minus_di:.1f}")
            
            print()
            print("SIGNAL CONDITIONS CHECK FOR SHORT:")
            
            below_vwap = entry_candle['Close'] < entry_candle['VWAP']
            print(f"  Price < VWAP: {'✅ YES' if below_vwap else '❌ NO'} ({entry_candle['Close']:.2f} vs {entry_candle['VWAP']:.2f})")
            
            st_bearish = entry_candle['ST_Dir'] == -1
            print(f"  Supertrend Bearish: {'✅ YES' if st_bearish else '❌ NO'} ({st_dir_text})")
            
            adx_ok = adx >= 20 and not adx_is_nan
            print(f"  ADX >= 20: {'✅ YES' if adx_ok else '❌ NO'} ({adx:.1f})")
            
            minus_di_higher = minus_di > plus_di
            print(f"  -DI > +DI (Bearish): {'✅ YES' if minus_di_higher else '❌ NO'} ({minus_di:.1f} vs {plus_di:.1f})")
            
            # Check ADX trend
            try:
                idx_loc = df_today.index.get_loc(entry_candle.name)
                if idx_loc > 0:
                    prev_adx = df_today['ADX'].iloc[idx_loc - 1]
                    adx_change = adx - prev_adx
                    adx_rising = adx_change > 0.5
                    print(f"  ADX Rising: {'✅ YES' if adx_rising else '❌ NO'} (Change: {adx_change:+.1f})")
            except:
                pass
            
            # With NEW rules
            print()
            print("WITH NEW STRICT RULES:")
            if st_is_nan:
                print("  ⛔ BLOCKED: Supertrend is NaN")
            elif not st_bearish:
                print(f"  ⛔ BLOCKED: Supertrend is {st_dir_text}, not BEARISH")
            elif adx_is_nan or adx < 20:
                print(f"  ⛔ BLOCKED: ADX is {adx:.1f} (need >= 20)")
            else:
                print("  ✅ Would be ALLOWED (ST is BEARISH + ADX >= 20)")
                
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    print("=" * 80)
    print("YOUR 6 TRADES TODAY - SUMMARY")
    print("=" * 80)
    print()
    print("| #  | Stock        | Direction | Time   | Result  | Valid? |")
    print("|----|--------------|-----------|--------|---------|--------|")
    print("| 1  | POLICYBZR    | SHORT     | 9:27   | -1.92%  | ❌ NaN |")
    print("| 2  | UNIONBANK    | LONG      | 10:08  | -0.38%  | ❌ NaN |")
    print("| 3  | KOTAKBANK    | SHORT     | 10:47  | +0.14%  | ❌ ADX<20 |")
    print("| 4  | TORNTPHARM   | SHORT     | 11:25  | -0.42%  | ❌ ST Bull |")
    print("| 5  | HINDUNILVR   | SHORT     | 11:40  | -0.11%  | ✅ Valid |")
    print(f"| 6  | ONGC         | SHORT     | 12:41  | -{loss_pct:.2f}%  | ??? |")

if __name__ == "__main__":
    main()
