#!/usr/bin/env python3
"""
SIDDHI DayTrade Quick Backtest
==============================
Quick backtest with fewer stocks for faster results.
Run: python3 backtest_quick.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Quick test stocks (10 liquid stocks)
STOCKS = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", 
          "SBIN", "KOTAKBANK", "LT", "AXISBANK", "TATAMOTORS"]

def calculate_vwap(high, low, close, volume):
    tp = (high + low + close) / 3
    vwap = (tp * volume).cumsum() / volume.cumsum()
    price = close.iloc[-1]
    v = vwap.iloc[-1]
    dist = ((price - v) / v) * 100
    signal = "BULLISH" if price > v * 1.002 else "BEARISH" if price < v * 0.998 else "NEUTRAL"
    return {"vwap": v, "signal": signal, "distance_pct": dist}

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
    
    bw = (upper.iloc[-1] - lower.iloc[-1]) / mid.iloc[-1] * 100
    prev_bw = (upper.iloc[-5] - lower.iloc[-5]) / mid.iloc[-5] * 100 if len(upper) > 5 else bw
    squeeze = bw < prev_bw * 0.8
    
    if pct_b > 100: sig = "OVERBOUGHT"
    elif pct_b < 0: sig = "OVERSOLD"
    elif pct_b > 80: sig = "BULLISH"
    elif pct_b < 20: sig = "BEARISH"
    else: sig = "NEUTRAL"
    
    return {"upper": upper.iloc[-1], "lower": lower.iloc[-1], "middle": mid.iloc[-1], 
            "signal": sig, "squeeze": squeeze, "percent_b": pct_b}

def calculate_adx(high, low, close, di_len=7, adx_smooth=7):
    if len(close) < di_len + adx_smooth + 5:
        return {"adx": 0, "trend_direction": "NEUTRAL", "weakening": False, "plus_di": 0, "minus_di": 0}
    
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
    
    return {
        "adx": curr, 
        "trend_direction": "BULLISH" if plus_di.iloc[-1] > minus_di.iloc[-1] else "BEARISH",
        "weakening": curr < prev and curr > 20,
        "plus_di": plus_di.iloc[-1], "minus_di": minus_di.iloc[-1]
    }

def calculate_roc(prices, period=10):
    if len(prices) < period + 5:
        return {"roc": 0, "signal": "NEUTRAL", "bearish_div": False, "bullish_div": False, "weakening": False}
    
    roc = ((prices.iloc[-1] - prices.iloc[-period]) / prices.iloc[-period]) * 100
    prev_roc = ((prices.iloc[-2] - prices.iloc[-period-1]) / prices.iloc[-period-1]) * 100
    
    price_hi = prices.iloc[-1] > prices.iloc[-5:-1].max()
    bear_div = price_hi and roc < prev_roc and roc > 0
    
    price_lo = prices.iloc[-1] < prices.iloc[-5:-1].min()
    bull_div = price_lo and roc > prev_roc and roc < 0
    
    sig = "BULLISH" if roc > 2 else "BEARISH" if roc < -2 else "NEUTRAL"
    return {"roc": roc, "signal": sig, "bearish_div": bear_div, "bullish_div": bull_div, "weakening": abs(roc) < abs(prev_roc)}

def analyze_signal(h5, h10, min_conf=4):
    if h5.empty or len(h5) < 50 or h10.empty or len(h10) < 20:
        return {"signal": "NONE", "confirmations": 0}
    
    ltp = h5['Close'].iloc[-1]
    
    # Core indicators
    vwap5 = calculate_vwap(h5['High'], h5['Low'], h5['Close'], h5['Volume'])
    st5 = calculate_supertrend(h5['High'], h5['Low'], h5['Close'])
    bb5 = calculate_bb(h5['Close'])
    
    vwap10 = calculate_vwap(h10['High'], h10['Low'], h10['Close'], h10['Volume'])
    st10 = calculate_supertrend(h10['High'], h10['Low'], h10['Close'])
    bb10 = calculate_bb(h10['Close'])
    
    # Advanced
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
    if bb5["squeeze"] and st5["signal"] == "BULLISH": lc += 1
    
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
    if bb5["squeeze"] and st5["signal"] == "BEARISH": sc += 1
    
    if adx["weakening"] and adx["trend_direction"] == "BEARISH": sc -= 1
    if roc["bullish_div"]: sc -= 2
    
    if lc >= min_conf and lc > sc:
        sl = max(bb5["lower"] * 0.998, st5["value"] * 0.995)
        t1 = min(bb5["upper"], ltp * 1.015)
        if sl >= ltp: sl = ltp * 0.993
        if t1 <= ltp: t1 = ltp * 1.01
        return {"signal": "LONG", "confirmations": lc, "entry": ltp, "stoploss": sl, "target1": t1}
    
    if sc >= min_conf and sc > lc:
        sl = min(bb5["upper"] * 1.002, st5["value"] * 1.005)
        t1 = max(bb5["lower"], ltp * 0.985)
        if sl <= ltp: sl = ltp * 1.007
        if t1 >= ltp: t1 = ltp * 0.99
        return {"signal": "SHORT", "confirmations": sc, "entry": ltp, "stoploss": sl, "target1": t1}
    
    return {"signal": "NONE", "confirmations": max(lc, sc)}

def check_outcome(h5, sig, entry_idx, max_candles=36):
    if sig["signal"] == "NONE":
        return {"outcome": "NONE", "pnl_pct": 0}
    
    entry, sl, t1 = sig["entry"], sig["stoploss"], sig["target1"]
    future = h5.iloc[entry_idx:min(entry_idx + max_candles, len(h5))]
    
    if future.empty:
        return {"outcome": "NO_DATA", "pnl_pct": 0}
    
    for i, (_, row) in enumerate(future.iterrows()):
        if sig["signal"] == "LONG":
            if row['Low'] <= sl:
                return {"outcome": "LOSS", "pnl_pct": ((sl - entry) / entry) * 100, "mins": (i+1)*5}
            if row['High'] >= t1:
                return {"outcome": "WIN", "pnl_pct": ((t1 - entry) / entry) * 100, "mins": (i+1)*5}
        else:
            if row['High'] >= sl:
                return {"outcome": "LOSS", "pnl_pct": ((entry - sl) / entry) * 100, "mins": (i+1)*5}
            if row['Low'] <= t1:
                return {"outcome": "WIN", "pnl_pct": ((entry - t1) / entry) * 100, "mins": (i+1)*5}
    
    # Expired
    final = future['Close'].iloc[-1]
    pnl = ((final - entry) / entry) * 100 if sig["signal"] == "LONG" else ((entry - final) / entry) * 100
    return {"outcome": "EXPIRED", "pnl_pct": pnl, "mins": len(future)*5}

def run_backtest():
    print("\n" + "="*60)
    print("🚀 SIDDHI DayTrade Quick Backtest (5-min Chart)")
    print("="*60)
    print(f"📊 Testing: {len(STOCKS)} stocks | Period: 5 days")
    print(f"🎯 Strategy: VWAP + Supertrend + BB + ADX(7,7) + ROC")
    print("="*60)
    
    all_trades = []
    
    for symbol in STOCKS:
        print(f"\n📈 {symbol}...", end=" ")
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            h5 = ticker.history(period="7d", interval="5m")
            
            if h5.empty or len(h5) < 100:
                print("❌ No data")
                continue
            
            h10 = h5.resample('10min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
            
            dates = pd.Series(h5.index.date if h5.index.tz is None else h5.index.tz_localize(None).date).unique()[-5:]
            
            trades = []
            for date in dates:
                day_mask = (h5.index.date if h5.index.tz is None else h5.index.tz_localize(None).date) == date
                day_idx = np.where(day_mask)[0]
                
                if len(day_idx) < 75:
                    continue
                
                for offset in [15, 33, 51]:  # 9:30, 11:00, 12:30
                    idx = day_idx[0] + offset
                    if idx >= len(h5) - 36:
                        continue
                    
                    sig = analyze_signal(h5.iloc[:idx+1], h10[h10.index <= h5.index[idx]])
                    
                    if sig["signal"] != "NONE":
                        out = check_outcome(h5, sig, idx)
                        trades.append({
                            "symbol": symbol, "signal": sig["signal"], 
                            "conf": sig["confirmations"], "outcome": out["outcome"],
                            "pnl": out["pnl_pct"]
                        })
                        all_trades.append(trades[-1])
            
            if trades:
                wins = sum(1 for t in trades if t["outcome"] == "WIN")
                pnl = sum(t["pnl"] for t in trades)
                print(f"✅ {len(trades)} trades | WR: {wins/len(trades)*100:.0f}% | P&L: {pnl:+.2f}%")
            else:
                print("⚪ No signals")
                
        except Exception as e:
            print(f"❌ {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 RESULTS SUMMARY")
    print("="*60)
    
    if not all_trades:
        print("❌ No trades")
        return
    
    total = len(all_trades)
    wins = sum(1 for t in all_trades if t["outcome"] == "WIN")
    losses = sum(1 for t in all_trades if t["outcome"] == "LOSS")
    expired = sum(1 for t in all_trades if t["outcome"] == "EXPIRED")
    
    wr = (wins / total) * 100
    pnl = sum(t["pnl"] for t in all_trades)
    
    longs = [t for t in all_trades if t["signal"] == "LONG"]
    shorts = [t for t in all_trades if t["signal"] == "SHORT"]
    
    long_wr = (sum(1 for t in longs if t["outcome"] == "WIN") / len(longs) * 100) if longs else 0
    short_wr = (sum(1 for t in shorts if t["outcome"] == "WIN") / len(shorts) * 100) if shorts else 0
    
    print(f"\n📈 Total Trades: {total}")
    print(f"   ✅ Wins: {wins} | ❌ Losses: {losses} | ⏰ Expired: {expired}")
    print(f"   🎯 Win Rate: {wr:.1f}%")
    print(f"   💰 Total P&L: {pnl:+.2f}%")
    
    print(f"\n📊 By Direction:")
    print(f"   🟢 LONG: {len(longs)} trades | Win Rate: {long_wr:.1f}%")
    print(f"   🔴 SHORT: {len(shorts)} trades | Win Rate: {short_wr:.1f}%")
    
    print(f"\n📊 By Confirmations:")
    for c in sorted(set(t["conf"] for t in all_trades)):
        ct = [t for t in all_trades if t["conf"] == c]
        cw = sum(1 for t in ct if t["outcome"] == "WIN")
        print(f"   {c} conf: {len(ct)} trades | WR: {cw/len(ct)*100:.0f}%")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    run_backtest()
