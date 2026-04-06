"""
Analyze Directional Success of UPDATED STRATEGY signals
Check if price moved in the right direction immediately after filtered signals
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import warnings
warnings.filterwarnings('ignore')

IST = pytz.timezone('Asia/Kolkata')

# Major stocks to analyze
MAJOR_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", 
    "KOTAKBANK", "HCLTECH", "ONGC", "SBIN", "BAJFINANCE", "MARUTI",
    "BHARTIARTL", "ITC", "AXISBANK", "LT", "TITAN", "WIPRO"
]

def calculate_supertrend(high, low, close, period=10, multiplier=3.0):
    if len(close) < period + 5:
        return pd.Series([np.nan]*len(close)), pd.Series([0]*len(close))
    
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

def calculate_adx(high, low, close, di_length=10, adx_smoothing=10):
    if len(close) < di_length + adx_smoothing + 5:
        return None
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=di_length).mean()
    
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    plus_dm_smooth = plus_dm.rolling(window=di_length).mean()
    minus_dm_smooth = minus_dm.rolling(window=di_length).mean()
    
    plus_di = 100 * (plus_dm_smooth / atr)
    minus_di = 100 * (minus_dm_smooth / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001)
    adx = dx.rolling(window=adx_smoothing).mean()
    
    return adx, plus_di, minus_di

def check_filters(idx, adx, plus_di, minus_di, st_dir):
    """Check all filters at a given index"""
    
    curr_adx = adx.iloc[idx]
    curr_plus_di = plus_di.iloc[idx]
    curr_minus_di = minus_di.iloc[idx]
    prev_plus_di = plus_di.iloc[idx-1] if idx > 0 else curr_plus_di
    prev_minus_di = minus_di.iloc[idx-1] if idx > 0 else curr_minus_di
    prev_adx = adx.iloc[idx-1] if idx > 0 else curr_adx
    
    # NaN check
    if pd.isna(curr_adx) or curr_adx == 0:
        return False
    
    # ADX < 20
    if curr_adx < 20:
        return False
    
    # ADX falling
    adx_change = curr_adx - prev_adx
    if adx_change < -0.5 and curr_adx > 15:
        return False
    
    # ADX not rising (unless >= 30)
    if adx_change <= 0.5 and curr_adx < 30:
        return False
    
    # ADX Exhaustion (> 80)
    if curr_adx > 80:
        return False
    
    # DI Gap Narrowing
    curr_gap = abs(curr_plus_di - curr_minus_di)
    prev_gap = abs(prev_plus_di - prev_minus_di)
    gap_change = curr_gap - prev_gap
    if gap_change < -1.0 and curr_gap < 15:
        return False
    
    return True

def analyze_stock(symbol):
    """Analyze a single stock for directional accuracy"""
    
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        df = ticker.history(period="5d", interval="5m")
        
        if len(df) < 25:
            return []
        
        last_day = df.index[-1].date()
        df_today = df[df.index.date == last_day].copy()
        
        if len(df_today) < 25:
            return []
        
        # Calculate indicators
        df_today['VWAP'] = calculate_vwap(df_today)
        st, st_dir = calculate_supertrend(df_today['High'], df_today['Low'], df_today['Close'])
        
        adx_result = calculate_adx(df_today['High'], df_today['Low'], df_today['Close'])
        if adx_result is None:
            return []
        
        adx, plus_di, minus_di = adx_result
        
        signals = []
        last_signal_idx = -10
        
        for idx in range(20, len(df_today) - 5):
            if idx - last_signal_idx < 3:
                continue
            
            # Check filters
            if not check_filters(idx, adx, plus_di, minus_di, st_dir):
                continue
            
            curr_close = df_today['Close'].iloc[idx]
            curr_vwap = df_today['VWAP'].iloc[idx]
            curr_st_dir = st_dir.iloc[idx]
            curr_plus_di = plus_di.iloc[idx]
            curr_minus_di = minus_di.iloc[idx]
            
            # Generate signal
            signal = None
            if curr_st_dir == 1 and curr_close > curr_vwap and curr_plus_di > curr_minus_di:
                signal = "LONG"
            elif curr_st_dir == -1 and curr_close < curr_vwap and curr_minus_di > curr_plus_di:
                signal = "SHORT"
            
            if signal is None:
                continue
            
            # Check ST direction
            if signal == "LONG" and curr_st_dir != 1:
                continue
            if signal == "SHORT" and curr_st_dir != -1:
                continue
            
            last_signal_idx = idx
            
            # Analyze directional accuracy
            entry_price = curr_close
            entry_time = df_today.index[idx].strftime('%H:%M')
            
            result = {
                "symbol": symbol,
                "time": entry_time,
                "signal": signal,
                "entry": entry_price,
                "adx": adx.iloc[idx]
            }
            
            # Check direction after 1, 3, 5 candles
            for candles, key in [(1, "1c"), (3, "3c"), (5, "5c")]:
                if idx + candles < len(df_today):
                    future_close = df_today['Close'].iloc[idx + candles]
                    if signal == "LONG":
                        result[f"{key}_correct"] = future_close > entry_price
                        result[f"{key}_move"] = ((future_close - entry_price) / entry_price) * 100
                    else:
                        result[f"{key}_correct"] = future_close < entry_price
                        result[f"{key}_move"] = ((entry_price - future_close) / entry_price) * 100
            
            signals.append(result)
        
        return signals
        
    except Exception as e:
        return []

def main():
    print("="*80)
    print("DIRECTIONAL SUCCESS ANALYSIS - UPDATED STRATEGY")
    print("="*80)
    print()
    print("Analyzing signals that PASS all new filters:")
    print("  ✓ ADX >= 20")
    print("  ✓ ADX Rising (or >= 30)")
    print("  ✓ ADX Not Falling")
    print("  ✓ ADX < 80 (not exhausted)")
    print("  ✓ DI Gap Not Narrowing")
    print("  ✓ Supertrend matches direction")
    print()
    
    all_signals = []
    
    for symbol in MAJOR_STOCKS:
        print(f"Processing {symbol}...", end=" ")
        signals = analyze_stock(symbol)
        all_signals.extend(signals)
        print(f"{len(signals)} signals")
    
    print()
    print("="*80)
    print("DIRECTIONAL ACCURACY RESULTS")
    print("="*80)
    print()
    
    if not all_signals:
        print("No signals generated")
        return
    
    # Calculate accuracy
    total = len(all_signals)
    correct_1c = sum(1 for s in all_signals if s.get("1c_correct", False))
    correct_3c = sum(1 for s in all_signals if s.get("3c_correct", False))
    correct_5c = sum(1 for s in all_signals if s.get("5c_correct", False))
    
    # By direction
    long_signals = [s for s in all_signals if s["signal"] == "LONG"]
    short_signals = [s for s in all_signals if s["signal"] == "SHORT"]
    
    long_1c = sum(1 for s in long_signals if s.get("1c_correct", False))
    short_1c = sum(1 for s in short_signals if s.get("1c_correct", False))
    
    print(f"Total Signals: {total}")
    print(f"  LONG: {len(long_signals)}")
    print(f"  SHORT: {len(short_signals)}")
    print()
    
    print("DIRECTIONAL ACCURACY (price moved in right direction):")
    print("-"*50)
    print(f"After 1 Candle (5 min):  {correct_1c}/{total} = {correct_1c/total*100:.1f}%")
    print(f"After 3 Candles (15 min): {correct_3c}/{total} = {correct_3c/total*100:.1f}%")
    print(f"After 5 Candles (25 min): {correct_5c}/{total} = {correct_5c/total*100:.1f}%")
    print()
    
    print("BY DIRECTION:")
    print(f"  LONG signals:  {long_1c}/{len(long_signals)} = {long_1c/len(long_signals)*100:.1f}% correct after 1 candle" if long_signals else "  LONG: N/A")
    print(f"  SHORT signals: {short_1c}/{len(short_signals)} = {short_1c/len(short_signals)*100:.1f}% correct after 1 candle" if short_signals else "  SHORT: N/A")
    print()
    
    # Average moves
    avg_1c = sum(s.get("1c_move", 0) for s in all_signals) / total
    avg_3c = sum(s.get("3c_move", 0) for s in all_signals) / total
    avg_5c = sum(s.get("5c_move", 0) for s in all_signals) / total
    
    print("AVERAGE MOVE IN YOUR DIRECTION:")
    print(f"  After 1 Candle: {avg_1c:+.3f}%")
    print(f"  After 3 Candles: {avg_3c:+.3f}%")
    print(f"  After 5 Candles: {avg_5c:+.3f}%")
    print()
    
    # Sample signals
    print("="*80)
    print("SAMPLE SIGNALS (first 20)")
    print("="*80)
    print()
    print(f"{'Time':<8} {'Symbol':<12} {'Signal':<6} {'ADX':>6} {'1c':>8} {'3c':>8} {'5c':>8}")
    print("-"*60)
    
    for s in all_signals[:20]:
        c1 = "✅" if s.get("1c_correct", False) else "❌"
        c3 = "✅" if s.get("3c_correct", False) else "❌"
        c5 = "✅" if s.get("5c_correct", False) else "❌"
        m1 = f"{s.get('1c_move', 0):+.2f}%"
        m3 = f"{s.get('3c_move', 0):+.2f}%"
        m5 = f"{s.get('5c_move', 0):+.2f}%"
        
        print(f"{s['time']:<8} {s['symbol']:<12} {s['signal']:<6} {s['adx']:>6.1f} {c1}{m1:>6} {c3}{m3:>6} {c5}{m5:>6}")
    
    print()
    print("="*80)
    print("COMPARISON: Your Trades vs Strategy")
    print("="*80)
    print()
    print(f"YOUR 9 TRADES TODAY:")
    print(f"  Direction correct after 1 candle: 22% (2/9)")
    print()
    print(f"UPDATED STRATEGY ({total} signals):")
    print(f"  Direction correct after 1 candle: {correct_1c/total*100:.1f}% ({correct_1c}/{total})")
    print()
    
    improvement = (correct_1c/total*100) - 22
    print(f"IMPROVEMENT: +{improvement:.1f} percentage points")

if __name__ == "__main__":
    main()
