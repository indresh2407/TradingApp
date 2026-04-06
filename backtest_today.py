"""
Backtest Today's DayTrade Signals
Analyzes what happened to signals generated today
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import warnings
warnings.filterwarnings('ignore')

# NIFTY 100 stocks (subset for faster testing)
NIFTY_100 = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "SBIN", 
    "BHARTIARTL", "KOTAKBANK", "ITC", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "BAJFINANCE", "HCLTECH", "WIPRO", "SUNPHARMA", "TITAN", "ULTRACEMCO",
    "NESTLEIND", "TECHM", "POWERGRID", "NTPC", "TATAMOTORS", "ONGC", "COALINDIA",
    "BAJAJFINSV", "ADANIPORTS", "JSWSTEEL", "TATASTEEL", "HINDALCO", "INDUSINDBK",
    "DRREDDY", "CIPLA", "GRASIM", "DIVISLAB", "BPCL", "EICHERMOT", "BRITANNIA",
    "HEROMOTOCO", "APOLLOHOSP", "SBILIFE", "HDFCLIFE", "BAJAJ-AUTO", "TATACONSUM",
    "M&M", "ADANIENT", "SHREECEM", "PIDILITIND"
]

IST = pytz.timezone('Asia/Kolkata')

def calculate_supertrend(df, period=10, multiplier=3):
    """Calculate Supertrend indicator"""
    hl2 = (df['High'] + df['Low']) / 2
    
    # ATR calculation
    tr1 = df['High'] - df['Low']
    tr2 = abs(df['High'] - df['Close'].shift(1))
    tr3 = abs(df['Low'] - df['Close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    # Supertrend bands
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    for i in range(period, len(df)):
        if df['Close'].iloc[i] > upper_band.iloc[i-1]:
            supertrend.iloc[i] = lower_band.iloc[i]
            direction.iloc[i] = 1  # Bullish
        elif df['Close'].iloc[i] < lower_band.iloc[i-1]:
            supertrend.iloc[i] = upper_band.iloc[i]
            direction.iloc[i] = -1  # Bearish
        else:
            supertrend.iloc[i] = supertrend.iloc[i-1]
            direction.iloc[i] = direction.iloc[i-1]
            
            if direction.iloc[i] == 1 and lower_band.iloc[i] > supertrend.iloc[i]:
                supertrend.iloc[i] = lower_band.iloc[i]
            elif direction.iloc[i] == -1 and upper_band.iloc[i] < supertrend.iloc[i]:
                supertrend.iloc[i] = upper_band.iloc[i]
    
    return supertrend, direction

def calculate_vwap(df):
    """Calculate VWAP"""
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    return vwap

def calculate_atr(df, period=14):
    """Calculate ATR"""
    tr1 = df['High'] - df['Low']
    tr2 = abs(df['High'] - df['Close'].shift(1))
    tr3 = abs(df['Low'] - df['Close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calculate_adx(df, di_length=10, adx_smoothing=10):
    """Calculate ADX"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window=di_length).mean()
    plus_di = 100 * (plus_dm.rolling(window=di_length).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=di_length).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=adx_smoothing).mean()
    
    return adx, plus_di, minus_di

def analyze_signal_outcome(df, signal_idx, signal_type, entry, stoploss, target1, target2):
    """
    Analyze what happened after a signal was generated
    Returns: outcome dict with result and details
    """
    if signal_idx >= len(df) - 1:
        return {"result": "NO_DATA", "reason": "Signal at end of day"}
    
    # Look at candles after signal
    future_df = df.iloc[signal_idx + 1:]
    
    if len(future_df) == 0:
        return {"result": "NO_DATA", "reason": "No future data"}
    
    # Track price action
    for i, (idx, row) in enumerate(future_df.iterrows()):
        if signal_type == "LONG":
            # Check if entry was achieved
            if row['Low'] <= entry:
                # Entry triggered, now check outcome
                for j, (idx2, row2) in enumerate(future_df.iloc[i:].iterrows()):
                    if row2['Low'] <= stoploss:
                        return {
                            "result": "SL_HIT",
                            "reason": f"Stoploss hit after {j+1} candles",
                            "candles_to_outcome": j + 1,
                            "loss_pct": ((stoploss - entry) / entry) * 100
                        }
                    if row2['High'] >= target1:
                        return {
                            "result": "T1_HIT",
                            "reason": f"Target 1 hit after {j+1} candles",
                            "candles_to_outcome": j + 1,
                            "profit_pct": ((target1 - entry) / entry) * 100
                        }
                    if row2['High'] >= target2:
                        return {
                            "result": "T2_HIT",
                            "reason": f"Target 2 hit after {j+1} candles",
                            "candles_to_outcome": j + 1,
                            "profit_pct": ((target2 - entry) / entry) * 100
                        }
                
                # Neither SL nor target hit - check final price
                final_price = future_df.iloc[-1]['Close']
                pnl_pct = ((final_price - entry) / entry) * 100
                return {
                    "result": "OPEN" if pnl_pct > 0 else "UNDERWATER",
                    "reason": f"Trade still open, PnL: {pnl_pct:.2f}%",
                    "pnl_pct": pnl_pct
                }
        
        else:  # SHORT
            if row['High'] >= entry:
                # Entry triggered, now check outcome
                for j, (idx2, row2) in enumerate(future_df.iloc[i:].iterrows()):
                    if row2['High'] >= stoploss:
                        return {
                            "result": "SL_HIT",
                            "reason": f"Stoploss hit after {j+1} candles",
                            "candles_to_outcome": j + 1,
                            "loss_pct": ((entry - stoploss) / entry) * 100
                        }
                    if row2['Low'] <= target1:
                        return {
                            "result": "T1_HIT",
                            "reason": f"Target 1 hit after {j+1} candles",
                            "candles_to_outcome": j + 1,
                            "profit_pct": ((entry - target1) / entry) * 100
                        }
                    if row2['Low'] <= target2:
                        return {
                            "result": "T2_HIT",
                            "reason": f"Target 2 hit after {j+1} candles",
                            "candles_to_outcome": j + 1,
                            "profit_pct": ((entry - target2) / entry) * 100
                        }
                
                # Neither SL nor target hit
                final_price = future_df.iloc[-1]['Close']
                pnl_pct = ((entry - final_price) / entry) * 100
                return {
                    "result": "OPEN" if pnl_pct > 0 else "UNDERWATER",
                    "reason": f"Trade still open, PnL: {pnl_pct:.2f}%",
                    "pnl_pct": pnl_pct
                }
    
    return {"result": "NO_ENTRY", "reason": "Entry price never reached"}

def generate_and_backtest_signals(symbol, df_5m, df_10m):
    """Generate signals and backtest them"""
    signals = []
    
    if len(df_5m) < 30 or len(df_10m) < 20:
        return signals
    
    # Calculate indicators for 5m
    df_5m['VWAP'] = calculate_vwap(df_5m)
    df_5m['ST'], df_5m['ST_Dir'] = calculate_supertrend(df_5m, 10, 3)
    df_5m['ATR'] = calculate_atr(df_5m, 14)
    df_5m['ADX'], df_5m['Plus_DI'], df_5m['Minus_DI'] = calculate_adx(df_5m, 10, 10)
    
    # Calculate indicators for 10m
    df_10m['VWAP'] = calculate_vwap(df_10m)
    df_10m['ST'], df_10m['ST_Dir'] = calculate_supertrend(df_10m, 10, 3)
    
    # Market hours: 9:15 AM to 3:30 PM IST
    market_open = datetime.now(IST).replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = datetime.now(IST).replace(hour=15, minute=0, second=0, microsecond=0)
    
    # Iterate through 5m candles looking for signals
    for i in range(20, len(df_5m) - 5):  # Leave room for outcome analysis
        row = df_5m.iloc[i]
        timestamp = row.name
        
        # Skip if outside market hours
        if hasattr(timestamp, 'hour'):
            if timestamp.hour < 9 or (timestamp.hour == 9 and timestamp.minute < 30):
                continue
            if timestamp.hour >= 15:
                continue
        
        ltp = row['Close']
        vwap_5m = row['VWAP']
        st_5m = row['ST']
        st_dir_5m = row['ST_Dir']
        atr = row['ATR']
        adx = row['ADX']
        plus_di = row['Plus_DI']
        minus_di = row['Minus_DI']
        
        if pd.isna(adx) or pd.isna(st_5m) or pd.isna(atr):
            continue
        
        # Find corresponding 10m data
        ts_10m = timestamp.floor('10T') if hasattr(timestamp, 'floor') else timestamp
        if ts_10m not in df_10m.index:
            continue
        
        row_10m = df_10m.loc[ts_10m]
        st_dir_10m = row_10m['ST_Dir']
        vwap_10m = row_10m['VWAP']
        
        # ADX filter - require rising ADX or strong trend
        adx_prev = df_5m['ADX'].iloc[i-1] if i > 0 else adx
        adx_change = adx - adx_prev
        adx_rising = adx_change > 0.5
        
        if adx < 20 or (not adx_rising and adx < 30):
            continue
        
        # LONG signal conditions
        long_conditions = 0
        if ltp > vwap_5m:
            long_conditions += 1
        if st_dir_5m == 1:
            long_conditions += 1
        if st_dir_10m == 1:
            long_conditions += 1
        if ltp > vwap_10m:
            long_conditions += 1
        if plus_di > minus_di:
            long_conditions += 1
        
        # SHORT signal conditions
        short_conditions = 0
        if ltp < vwap_5m:
            short_conditions += 1
        if st_dir_5m == -1:
            short_conditions += 1
        if st_dir_10m == -1:
            short_conditions += 1
        if ltp < vwap_10m:
            short_conditions += 1
        if minus_di > plus_di:
            short_conditions += 1
        
        # Generate signal if enough confirmations
        if long_conditions >= 4:
            entry = round(ltp * 0.9985, 2)  # 0.15% pullback
            stoploss = round(entry - (atr * 1.5), 2)
            target1 = round(entry + (atr * 1.0), 2)
            target2 = round(entry + (atr * 1.5), 2)
            
            outcome = analyze_signal_outcome(df_5m, i, "LONG", entry, stoploss, target1, target2)
            
            signals.append({
                "symbol": symbol,
                "time": str(timestamp),
                "type": "LONG",
                "ltp": ltp,
                "entry": entry,
                "stoploss": stoploss,
                "target1": target1,
                "target2": target2,
                "adx": round(adx, 1),
                "adx_rising": adx_rising,
                "confirmations": long_conditions,
                "outcome": outcome
            })
        
        elif short_conditions >= 4:
            entry = round(ltp * 1.0015, 2)  # 0.15% bounce
            stoploss = round(entry + (atr * 1.5), 2)
            target1 = round(entry - (atr * 1.0), 2)
            target2 = round(entry - (atr * 1.5), 2)
            
            outcome = analyze_signal_outcome(df_5m, i, "SHORT", entry, stoploss, target1, target2)
            
            signals.append({
                "symbol": symbol,
                "time": str(timestamp),
                "type": "SHORT",
                "ltp": ltp,
                "entry": entry,
                "stoploss": stoploss,
                "target1": target1,
                "target2": target2,
                "adx": round(adx, 1),
                "adx_rising": adx_rising,
                "confirmations": short_conditions,
                "outcome": outcome
            })
    
    return signals

def main():
    print("=" * 80)
    print("DAYTRADE BACKTEST - TODAY'S SIGNALS")
    print("=" * 80)
    print(f"Date: {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
    print()
    
    all_signals = []
    errors = []
    
    print(f"Analyzing {len(NIFTY_100)} stocks...")
    print()
    
    for i, symbol in enumerate(NIFTY_100):
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            
            # Get today's 5-minute data
            df_5m = ticker.history(period="1d", interval="5m")
            df_10m = ticker.history(period="1d", interval="15m")  # Use 15m as proxy for 10m
            
            if len(df_5m) > 20 and len(df_10m) > 10:
                signals = generate_and_backtest_signals(symbol, df_5m, df_10m)
                all_signals.extend(signals)
                
                if signals:
                    print(f"  {symbol}: {len(signals)} signals")
            
        except Exception as e:
            errors.append(f"{symbol}: {str(e)[:50]}")
            continue
        
        # Progress
        if (i + 1) % 10 == 0:
            print(f"Progress: {i+1}/{len(NIFTY_100)} stocks processed...")
    
    print()
    print("=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    
    if not all_signals:
        print("No signals generated today!")
        return
    
    # Analyze outcomes
    total = len(all_signals)
    t1_hits = sum(1 for s in all_signals if s["outcome"]["result"] == "T1_HIT")
    t2_hits = sum(1 for s in all_signals if s["outcome"]["result"] == "T2_HIT")
    sl_hits = sum(1 for s in all_signals if s["outcome"]["result"] == "SL_HIT")
    no_entry = sum(1 for s in all_signals if s["outcome"]["result"] == "NO_ENTRY")
    open_trades = sum(1 for s in all_signals if s["outcome"]["result"] in ["OPEN", "UNDERWATER"])
    no_data = sum(1 for s in all_signals if s["outcome"]["result"] == "NO_DATA")
    
    winners = t1_hits + t2_hits
    losers = sl_hits
    
    print(f"\nTotal Signals: {total}")
    print(f"  LONG:  {sum(1 for s in all_signals if s['type'] == 'LONG')}")
    print(f"  SHORT: {sum(1 for s in all_signals if s['type'] == 'SHORT')}")
    print()
    
    print("OUTCOMES:")
    print(f"  ✅ T1 Hit (Win):     {t1_hits} ({t1_hits/total*100:.1f}%)")
    print(f"  ✅ T2 Hit (Win):     {t2_hits} ({t2_hits/total*100:.1f}%)")
    print(f"  ❌ SL Hit (Loss):    {sl_hits} ({sl_hits/total*100:.1f}%)")
    print(f"  ⏳ No Entry:         {no_entry} ({no_entry/total*100:.1f}%)")
    print(f"  ⏳ Still Open:       {open_trades} ({open_trades/total*100:.1f}%)")
    print()
    
    if winners + losers > 0:
        win_rate = winners / (winners + losers) * 100
        print(f"WIN RATE: {win_rate:.1f}% ({winners} wins / {winners + losers} completed trades)")
    
    # Calculate average profit/loss
    profits = [s["outcome"].get("profit_pct", 0) for s in all_signals if "profit_pct" in s["outcome"]]
    losses = [s["outcome"].get("loss_pct", 0) for s in all_signals if "loss_pct" in s["outcome"]]
    
    if profits:
        print(f"Avg Profit (winners): +{np.mean(profits):.2f}%")
    if losses:
        print(f"Avg Loss (losers): {np.mean(losses):.2f}%")
    
    # Show failed signals for analysis
    print()
    print("=" * 80)
    print("FAILED SIGNALS ANALYSIS (SL Hit)")
    print("=" * 80)
    
    failed = [s for s in all_signals if s["outcome"]["result"] == "SL_HIT"]
    
    if failed:
        for s in failed[:10]:  # Show first 10
            print(f"\n{s['symbol']} {s['type']} @ {s['time']}")
            print(f"  Entry: ₹{s['entry']:.2f} | SL: ₹{s['stoploss']:.2f} | T1: ₹{s['target1']:.2f}")
            print(f"  ADX: {s['adx']} {'↑' if s['adx_rising'] else '↓'} | Confirmations: {s['confirmations']}")
            print(f"  Outcome: {s['outcome']['reason']}")
            print(f"  Loss: {s['outcome'].get('loss_pct', 0):.2f}%")
    else:
        print("No failed signals!")
    
    # Show winning signals
    print()
    print("=" * 80)
    print("WINNING SIGNALS (T1/T2 Hit)")
    print("=" * 80)
    
    winners_list = [s for s in all_signals if s["outcome"]["result"] in ["T1_HIT", "T2_HIT"]]
    
    if winners_list:
        for s in winners_list[:10]:
            print(f"\n{s['symbol']} {s['type']} @ {s['time']}")
            print(f"  Entry: ₹{s['entry']:.2f} | SL: ₹{s['stoploss']:.2f} | T1: ₹{s['target1']:.2f}")
            print(f"  ADX: {s['adx']} {'↑' if s['adx_rising'] else '↓'} | Confirmations: {s['confirmations']}")
            print(f"  Outcome: {s['outcome']['reason']}")
            print(f"  Profit: +{s['outcome'].get('profit_pct', 0):.2f}%")
    else:
        print("No winning signals!")
    
    # Identify patterns in failures
    print()
    print("=" * 80)
    print("FAILURE PATTERN ANALYSIS")
    print("=" * 80)
    
    if failed:
        # ADX analysis
        avg_adx_failed = np.mean([s['adx'] for s in failed])
        avg_adx_winners = np.mean([s['adx'] for s in winners_list]) if winners_list else 0
        print(f"\nAvg ADX in Failed: {avg_adx_failed:.1f}")
        print(f"Avg ADX in Winners: {avg_adx_winners:.1f}")
        
        # ADX rising analysis
        failed_rising = sum(1 for s in failed if s['adx_rising'])
        winners_rising = sum(1 for s in winners_list if s['adx_rising']) if winners_list else 0
        print(f"\nADX Rising in Failed: {failed_rising}/{len(failed)} ({failed_rising/len(failed)*100:.0f}%)")
        if winners_list:
            print(f"ADX Rising in Winners: {winners_rising}/{len(winners_list)} ({winners_rising/len(winners_list)*100:.0f}%)")
        
        # Time analysis
        print("\nSignals by Time (Failed):")
        for s in failed:
            time_str = s['time'].split(' ')[1][:5] if ' ' in s['time'] else s['time'][:5]
            print(f"  {s['symbol']} {s['type']} @ {time_str}")
    
    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if losers > winners:
        print("\n⚠️  More losses than wins today!")
        print("\nPossible improvements:")
        print("  1. Increase ADX threshold (current: 20, try: 25)")
        print("  2. Require more confirmations (current: 4, try: 5)")
        print("  3. Tighten stoploss (current: 1.5x ATR, try: 1.2x ATR)")
        print("  4. Check market trend before trading (avoid trading against market)")
        print("  5. Avoid first 30 min and last 30 min of market")
    else:
        print("\n✅ Strategy performing well today!")

if __name__ == "__main__":
    main()
