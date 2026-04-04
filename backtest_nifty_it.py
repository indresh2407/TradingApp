#!/usr/bin/env python3
"""
SIDDHI DayTrade - NIFTY IT Direction Accuracy
==============================================
Tests directional accuracy for NIFTY IT stocks only.

Run: python3 backtest_nifty_it.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# NIFTY IT stocks
NIFTY_IT = [
    "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM",
    "LTIM", "MPHASIS", "COFORGE", "PERSISTENT", "LTTS"
]

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]

def calculate_vwap(high, low, close, volume):
    tp = (high + low + close) / 3
    vwap = (tp * volume).cumsum() / volume.cumsum()
    price = close.iloc[-1]
    v = vwap.iloc[-1]
    return {"vwap": v, "signal": "BULLISH" if price > v * 1.002 else "BEARISH" if price < v * 0.998 else "NEUTRAL"}

def calculate_supertrend(high, low, close, period=10, mult=3.0):
    hl2 = (high + low) / 2
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    upper = hl2 + mult * atr
    lower = hl2 - mult * atr
    
    direction = pd.Series(index=close.index, dtype=int)
    st = pd.Series(index=close.index, dtype=float)
    
    for i in range(period, len(close)):
        if close.iloc[i] > upper.iloc[i-1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1] if i > period else 1
        st.iloc[i] = lower.iloc[i] if direction.iloc[i] == 1 else upper.iloc[i]
    
    d = direction.iloc[-1]
    cross = d != direction.iloc[-2] if len(direction) > 1 else False
    return {"value": st.iloc[-1], "signal": "BULLISH" if d == 1 else "BEARISH", "crossover": cross}

def calculate_bb(close, period=20, std=2.0):
    mid = close.rolling(period).mean()
    s = close.rolling(period).std()
    upper = mid + std * s
    lower = mid - std * s
    
    price = close.iloc[-1]
    pct_b = ((price - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])) * 100
    
    if pct_b > 100: sig = "OVERBOUGHT"
    elif pct_b < 0: sig = "OVERSOLD"
    elif pct_b > 80: sig = "BULLISH"
    elif pct_b < 20: sig = "BEARISH"
    else: sig = "NEUTRAL"
    
    return {"upper": upper.iloc[-1], "lower": lower.iloc[-1], "signal": sig}

def calculate_adx(high, low, close, di_len=7, adx_smooth=7):
    if len(close) < di_len + adx_smooth + 5:
        return {"adx": 0, "trend_direction": "NEUTRAL", "weakening": False}
    
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(di_len).mean()
    
    plus_dm = high.diff().where((high.diff() > -low.diff()) & (high.diff() > 0), 0)
    minus_dm = (-low.diff()).where((-low.diff() > high.diff()) & (-low.diff() > 0), 0)
    
    plus_di = 100 * plus_dm.rolling(di_len).mean() / atr
    minus_di = 100 * minus_dm.rolling(di_len).mean() / atr
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001)
    adx = dx.rolling(adx_smooth).mean()
    
    curr = adx.iloc[-1]
    prev = adx.iloc[-2] if len(adx) > 1 else curr
    
    return {"adx": curr, "trend_direction": "BULLISH" if plus_di.iloc[-1] > minus_di.iloc[-1] else "BEARISH", "weakening": curr < prev and curr > 20}

def calculate_roc(prices, period=10):
    if len(prices) < period + 5:
        return {"roc": 0, "signal": "NEUTRAL", "bearish_div": False, "bullish_div": False}
    
    roc = ((prices.iloc[-1] - prices.iloc[-period]) / prices.iloc[-period]) * 100
    prev_roc = ((prices.iloc[-2] - prices.iloc[-period-1]) / prices.iloc[-period-1]) * 100
    
    bear_div = prices.iloc[-1] > prices.iloc[-5:-1].max() and roc < prev_roc and roc > 0
    bull_div = prices.iloc[-1] < prices.iloc[-5:-1].min() and roc > prev_roc and roc < 0
    
    return {"roc": roc, "signal": "BULLISH" if roc > 2 else "BEARISH" if roc < -2 else "NEUTRAL", 
            "bearish_div": bear_div, "bullish_div": bull_div, "weakening": abs(roc) < abs(prev_roc)}

def analyze_signal(h5, h10, min_conf=4):
    if h5.empty or len(h5) < 50 or h10.empty or len(h10) < 20:
        return None
    
    ltp = h5['Close'].iloc[-1]
    
    vwap5 = calculate_vwap(h5['High'], h5['Low'], h5['Close'], h5['Volume'])
    st5 = calculate_supertrend(h5['High'], h5['Low'], h5['Close'])
    bb5 = calculate_bb(h5['Close'])
    
    vwap10 = calculate_vwap(h10['High'], h10['Low'], h10['Close'], h10['Volume'])
    st10 = calculate_supertrend(h10['High'], h10['Low'], h10['Close'])
    bb10 = calculate_bb(h10['Close'])
    
    adx = calculate_adx(h5['High'], h5['Low'], h5['Close'])
    roc = calculate_roc(h5['Close'])
    
    # LONG
    lc = 0
    if vwap5["signal"] == "BULLISH": lc += 1
    if st5["signal"] == "BULLISH": lc += 1; lc += 1 if st5["crossover"] else 0
    if bb5["signal"] in ["OVERSOLD", "BULLISH"]: lc += 1
    if vwap10["signal"] == "BULLISH": lc += 1
    if st10["signal"] == "BULLISH": lc += 1; lc += 1 if st10["crossover"] else 0
    if bb10["signal"] in ["OVERSOLD", "BULLISH"]: lc += 1
    if adx["adx"] >= 25 and adx["trend_direction"] == "BULLISH": lc += 1
    if roc["signal"] == "BULLISH" and not roc["weakening"]: lc += 1
    if roc["bullish_div"]: lc += 2
    if adx["weakening"] and adx["trend_direction"] == "BULLISH": lc -= 1
    if roc["bearish_div"]: lc -= 2
    
    # SHORT
    sc = 0
    if vwap5["signal"] == "BEARISH": sc += 1
    if st5["signal"] == "BEARISH": sc += 1; sc += 1 if st5["crossover"] else 0
    if bb5["signal"] in ["OVERBOUGHT", "BEARISH"]: sc += 1
    if vwap10["signal"] == "BEARISH": sc += 1
    if st10["signal"] == "BEARISH": sc += 1; sc += 1 if st10["crossover"] else 0
    if bb10["signal"] in ["OVERBOUGHT", "BEARISH"]: sc += 1
    if adx["adx"] >= 25 and adx["trend_direction"] == "BEARISH": sc += 1
    if roc["signal"] == "BEARISH" and not roc["weakening"]: sc += 1
    if roc["bearish_div"]: sc += 2
    if adx["weakening"] and adx["trend_direction"] == "BEARISH": sc -= 1
    if roc["bullish_div"]: sc -= 2
    
    if lc >= min_conf and lc > sc:
        return {"signal": "LONG", "confirmations": lc, "entry": ltp}
    if sc >= min_conf and sc > lc:
        return {"signal": "SHORT", "confirmations": sc, "entry": ltp}
    return None

def check_direction(h5, sig, entry_idx, check_candles=12):
    if not sig:
        return None
    
    entry = sig["entry"]
    future = h5.iloc[entry_idx:min(entry_idx + check_candles, len(h5))]
    
    if future.empty or len(future) < 2:
        return None
    
    max_high = future['High'].max()
    min_low = future['Low'].min()
    close_final = future['Close'].iloc[-1]
    
    if sig["signal"] == "LONG":
        max_favorable = ((max_high - entry) / entry) * 100
        max_adverse = ((entry - min_low) / entry) * 100
        final_pnl = ((close_final - entry) / entry) * 100
        direction_correct = max_favorable >= 0.1
    else:
        max_favorable = ((entry - min_low) / entry) * 100
        max_adverse = ((max_high - entry) / entry) * 100
        final_pnl = ((entry - close_final) / entry) * 100
        direction_correct = max_favorable >= 0.1
    
    return {
        "direction_correct": direction_correct,
        "strong_move": max_favorable > max_adverse,
        "max_favorable": round(max_favorable, 2),
        "max_adverse": round(max_adverse, 2),
        "final_pnl": round(final_pnl, 2)
    }

def run_backtest():
    print("\n" + "="*60)
    print("🎯 NIFTY IT - Direction Accuracy Backtest")
    print("="*60)
    print(f"📊 Stocks: {', '.join(NIFTY_IT)}")
    print(f"⏱️  Check Window: 1 hour (12 candles on 5-min)")
    print("="*60)
    
    all_trades = []
    
    for symbol in NIFTY_IT:
        print(f"\n📈 {symbol}...", end=" ")
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            h5 = ticker.history(period="5d", interval="5m")
            
            if h5.empty or len(h5) < 100:
                print("❌ No data")
                continue
            
            h10 = h5.resample('10min').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 
                'Close': 'last', 'Volume': 'sum'
            }).dropna()
            
            # Get today's date
            if h5.index.tz is not None:
                dates = h5.index.tz_localize(None).date
            else:
                dates = h5.index.date
            
            today = pd.Series(dates).unique()[-1]  # Last trading day
            
            trades = []
            day_mask = dates == today
            day_idx = np.where(day_mask)[0]
            
            if len(day_idx) < 50:
                # If today has limited data, use yesterday
                today = pd.Series(dates).unique()[-2] if len(pd.Series(dates).unique()) > 1 else today
                day_mask = dates == today
                day_idx = np.where(day_mask)[0]
            
            if len(day_idx) < 30:
                print("❌ Insufficient data")
                continue
            
            # Test at multiple times
            for offset in [15, 27, 39, 51, 63]:  # 9:30, 10:15, 11:00, 11:45, 12:30
                idx = day_idx[0] + offset
                if idx >= len(h5) - 12:
                    continue
                
                sig = analyze_signal(h5.iloc[:idx+1], h10[h10.index <= h5.index[idx]])
                
                if sig:
                    out = check_direction(h5, sig, idx)
                    if out:
                        trade = {
                            "symbol": symbol,
                            "signal": sig["signal"],
                            "conf": sig["confirmations"],
                            "entry": sig["entry"],
                            **out
                        }
                        trades.append(trade)
                        all_trades.append(trade)
            
            if trades:
                correct = sum(1 for t in trades if t["direction_correct"])
                accuracy = (correct / len(trades)) * 100
                avg_fav = np.mean([t["max_favorable"] for t in trades])
                print(f"✅ {len(trades)} signals | Direction: {accuracy:.0f}% | Avg Move: +{avg_fav:.2f}%")
                
                # Show each signal
                for t in trades:
                    icon = "✅" if t["direction_correct"] else "❌"
                    print(f"      {icon} {t['signal']} @ ₹{t['entry']:.0f} | +{t['max_favorable']:.2f}% / -{t['max_adverse']:.2f}%")
            else:
                print("⚪ No signals")
                
        except Exception as e:
            print(f"❌ {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 NIFTY IT - DIRECTION ACCURACY SUMMARY")
    print("="*60)
    
    if not all_trades:
        print("❌ No trades generated")
        return
    
    total = len(all_trades)
    correct = sum(1 for t in all_trades if t["direction_correct"])
    strong = sum(1 for t in all_trades if t["strong_move"])
    
    accuracy = (correct / total) * 100
    strong_rate = (strong / total) * 100
    
    avg_favorable = np.mean([t["max_favorable"] for t in all_trades])
    avg_adverse = np.mean([t["max_adverse"] for t in all_trades])
    avg_pnl = np.mean([t["final_pnl"] for t in all_trades])
    
    print(f"\n🎯 DIRECTION ACCURACY: {accuracy:.1f}% ({correct}/{total} correct)")
    print(f"💪 STRONG MOVES: {strong_rate:.1f}% ({strong}/{total})")
    print(f"\n📈 MOVE ANALYSIS:")
    print(f"   Avg Favorable: +{avg_favorable:.2f}%")
    print(f"   Avg Adverse:   -{avg_adverse:.2f}%")
    print(f"   Avg Final P&L: {avg_pnl:+.2f}%")
    
    # By direction
    longs = [t for t in all_trades if t["signal"] == "LONG"]
    shorts = [t for t in all_trades if t["signal"] == "SHORT"]
    
    print(f"\n📊 BY DIRECTION:")
    if longs:
        long_acc = (sum(1 for t in longs if t["direction_correct"]) / len(longs)) * 100
        print(f"   🟢 LONG:  {len(longs)} signals | Accuracy: {long_acc:.0f}%")
    if shorts:
        short_acc = (sum(1 for t in shorts if t["direction_correct"]) / len(shorts)) * 100
        print(f"   🔴 SHORT: {len(shorts)} signals | Accuracy: {short_acc:.0f}%")
    
    # By stock
    print(f"\n📊 BY STOCK:")
    for sym in NIFTY_IT:
        st = [t for t in all_trades if t["symbol"] == sym]
        if st:
            s_correct = sum(1 for t in st if t["direction_correct"])
            s_acc = (s_correct / len(st)) * 100
            print(f"   {sym}: {s_acc:.0f}% ({s_correct}/{len(st)})")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    run_backtest()
