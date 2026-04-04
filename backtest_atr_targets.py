#!/usr/bin/env python3
"""
SIDDHI DayTrade Backtest - ATR-Based Targets v2
================================================
Tests the NEW strategy with ATR-based stops and targets.

Compares:
- OLD: BB-based targets (often too far)
- NEW: ATR-based targets (more achievable)

Run: python3 backtest_atr_targets.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Test stocks
STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "SBIN", "KOTAKBANK", "LT", "AXISBANK", "TATAMOTORS",
    "HINDUNILVR", "BHARTIARTL", "ITC", "MARUTI", "HCLTECH",
    "WIPRO", "BAJFINANCE", "SUNPHARMA", "TITAN", "ADANIENT"
]

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]

def calculate_vwap(high, low, close, volume):
    tp = (high + low + close) / 3
    vwap = (tp * volume).cumsum() / volume.cumsum()
    price = close.iloc[-1]
    v = vwap.iloc[-1]
    signal = "BULLISH" if price > v * 1.002 else "BEARISH" if price < v * 0.998 else "NEUTRAL"
    return {"vwap": v, "signal": signal}

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
            "signal": sig, "squeeze": squeeze}

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
    
    return {
        "adx": curr, 
        "trend_direction": "BULLISH" if plus_di.iloc[-1] > minus_di.iloc[-1] else "BEARISH",
        "weakening": curr < prev and curr > 20
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


def analyze_signal_with_targets(h5, h10, min_conf=4):
    """
    Analyze and return signal with BOTH old and new target calculations
    """
    if h5.empty or len(h5) < 50 or h10.empty or len(h10) < 20:
        return None
    
    ltp = h5['Close'].iloc[-1]
    atr = calculate_atr(h5['High'], h5['Low'], h5['Close'])
    
    # Get day's data
    today_data = h5.tail(75)
    day_high = today_data['High'].max()
    day_low = today_data['Low'].min()
    
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
    
    # LONG confirmations
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
    
    # SHORT confirmations
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
    
    has_crossover = st5["crossover"] or st10["crossover"]
    
    if lc >= min_conf and lc > sc:
        # OLD targets (BB-based)
        old_sl = max(bb5["lower"] * 0.998, st5["value"] * 0.995, day_low * 0.998)
        old_t1 = min(bb5["upper"], day_high * 1.002)
        old_t2 = max(bb5["upper"] * 1.01, day_high * 1.005)
        
        # NEW targets (ATR-based)
        atr_stop = ltp - (atr * 1.5)
        level_stop = max(st5["value"] * 0.997, day_low * 0.998)
        new_sl = max(atr_stop, level_stop)
        
        if has_crossover:
            new_t1 = ltp + (atr * 1.2)
            new_t2 = ltp + (atr * 2.0)
        else:
            new_t1 = ltp + (atr * 1.0)
            new_t2 = min(ltp + (atr * 1.5), bb5["upper"])
        
        return {
            "signal": "LONG",
            "confirmations": lc,
            "entry": ltp,
            "atr": atr,
            "has_crossover": has_crossover,
            "old_sl": old_sl, "old_t1": old_t1, "old_t2": old_t2,
            "new_sl": new_sl, "new_t1": new_t1, "new_t2": new_t2
        }
    
    if sc >= min_conf and sc > lc:
        # OLD targets (BB-based)
        old_sl = min(bb5["upper"] * 1.002, st5["value"] * 1.005, day_high * 1.002)
        old_t1 = max(bb5["lower"], day_low * 0.998)
        old_t2 = min(bb5["lower"] * 0.99, day_low * 0.995)
        
        # NEW targets (ATR-based)
        atr_stop = ltp + (atr * 1.5)
        level_stop = min(st5["value"] * 1.003, day_high * 1.002)
        new_sl = min(atr_stop, level_stop)
        
        if has_crossover:
            new_t1 = ltp - (atr * 1.2)
            new_t2 = ltp - (atr * 2.0)
        else:
            new_t1 = ltp - (atr * 1.0)
            new_t2 = max(ltp - (atr * 1.5), bb5["lower"])
        
        return {
            "signal": "SHORT",
            "confirmations": sc,
            "entry": ltp,
            "atr": atr,
            "has_crossover": has_crossover,
            "old_sl": old_sl, "old_t1": old_t1, "old_t2": old_t2,
            "new_sl": new_sl, "new_t1": new_t1, "new_t2": new_t2
        }
    
    return None


def check_outcome(h5, sig, entry_idx, sl, t1, t2, max_candles=36):
    """Check if target or stoploss was hit"""
    entry = sig["entry"]
    future = h5.iloc[entry_idx:min(entry_idx + max_candles, len(h5))]
    
    if future.empty or len(future) < 2:
        return {"outcome": "NO_DATA", "pnl": 0}
    
    for i, (_, row) in enumerate(future.iterrows()):
        if sig["signal"] == "LONG":
            if row['Low'] <= sl:
                return {"outcome": "LOSS", "pnl": ((sl - entry) / entry) * 100, "candles": i+1}
            if row['High'] >= t2:
                return {"outcome": "WIN_T2", "pnl": ((t2 - entry) / entry) * 100, "candles": i+1}
            if row['High'] >= t1:
                return {"outcome": "WIN_T1", "pnl": ((t1 - entry) / entry) * 100, "candles": i+1}
        else:
            if row['High'] >= sl:
                return {"outcome": "LOSS", "pnl": ((entry - sl) / entry) * 100, "candles": i+1}
            if row['Low'] <= t2:
                return {"outcome": "WIN_T2", "pnl": ((entry - t2) / entry) * 100, "candles": i+1}
            if row['Low'] <= t1:
                return {"outcome": "WIN_T1", "pnl": ((entry - t1) / entry) * 100, "candles": i+1}
    
    # Expired
    final = future['Close'].iloc[-1]
    pnl = ((final - entry) / entry) * 100 if sig["signal"] == "LONG" else ((entry - final) / entry) * 100
    return {"outcome": "EXPIRED", "pnl": pnl, "candles": len(future)}


def run_backtest():
    print("\n" + "="*70)
    print("🎯 SIDDHI DayTrade - OLD vs NEW Targets Comparison")
    print("="*70)
    print(f"📊 Testing: {len(STOCKS)} stocks | Period: Last 5 days")
    print(f"\n📐 OLD Method: BB-based targets (often 1.5-2% away)")
    print(f"📐 NEW Method: ATR-based targets (1-1.5x ATR, more achievable)")
    print("="*70)
    
    old_trades = []
    new_trades = []
    
    for symbol in STOCKS:
        print(f"\n📈 {symbol}...", end=" ")
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            h5 = ticker.history(period="7d", interval="5m")
            
            if h5.empty or len(h5) < 100:
                print("❌ No data")
                continue
            
            h10 = h5.resample('10min').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 
                'Close': 'last', 'Volume': 'sum'
            }).dropna()
            
            dates = pd.Series(h5.index.date if h5.index.tz is None else h5.index.tz_localize(None).date).unique()[-5:]
            
            symbol_old = []
            symbol_new = []
            
            for date in dates:
                day_mask = (h5.index.date if h5.index.tz is None else h5.index.tz_localize(None).date) == date
                day_idx = np.where(day_mask)[0]
                
                if len(day_idx) < 75:
                    continue
                
                for offset in [15, 33, 51, 69]:  # 9:30, 11:00, 12:30, 14:00
                    idx = day_idx[0] + offset
                    if idx >= len(h5) - 36:
                        continue
                    
                    sig = analyze_signal_with_targets(h5.iloc[:idx+1], h10[h10.index <= h5.index[idx]])
                    
                    if sig:
                        # Test OLD targets
                        old_out = check_outcome(h5, sig, idx, sig["old_sl"], sig["old_t1"], sig["old_t2"])
                        old_trades.append({
                            "symbol": symbol, "signal": sig["signal"], "conf": sig["confirmations"],
                            "outcome": old_out["outcome"], "pnl": old_out["pnl"]
                        })
                        symbol_old.append(old_out)
                        
                        # Test NEW targets
                        new_out = check_outcome(h5, sig, idx, sig["new_sl"], sig["new_t1"], sig["new_t2"])
                        new_trades.append({
                            "symbol": symbol, "signal": sig["signal"], "conf": sig["confirmations"],
                            "outcome": new_out["outcome"], "pnl": new_out["pnl"]
                        })
                        symbol_new.append(new_out)
            
            if symbol_old:
                old_wins = sum(1 for t in symbol_old if t["outcome"] in ["WIN_T1", "WIN_T2"])
                new_wins = sum(1 for t in symbol_new if t["outcome"] in ["WIN_T1", "WIN_T2"])
                old_wr = (old_wins / len(symbol_old)) * 100
                new_wr = (new_wins / len(symbol_new)) * 100
                
                change = "📈" if new_wr > old_wr else "📉" if new_wr < old_wr else "➖"
                print(f"✅ {len(symbol_old)} signals | OLD: {old_wr:.0f}% | NEW: {new_wr:.0f}% {change}")
            else:
                print("⚪ No signals")
                
        except Exception as e:
            print(f"❌ {e}")
    
    # ============== COMPARISON SUMMARY ==============
    print("\n" + "="*70)
    print("📊 COMPARISON: OLD vs NEW TARGET METHOD")
    print("="*70)
    
    if not old_trades:
        print("❌ No trades generated")
        return
    
    # OLD Method Stats
    old_total = len(old_trades)
    old_wins = sum(1 for t in old_trades if t["outcome"] in ["WIN_T1", "WIN_T2"])
    old_losses = sum(1 for t in old_trades if t["outcome"] == "LOSS")
    old_expired = sum(1 for t in old_trades if t["outcome"] == "EXPIRED")
    old_wr = (old_wins / old_total) * 100
    old_pnl = sum(t["pnl"] for t in old_trades)
    
    # NEW Method Stats
    new_total = len(new_trades)
    new_wins = sum(1 for t in new_trades if t["outcome"] in ["WIN_T1", "WIN_T2"])
    new_losses = sum(1 for t in new_trades if t["outcome"] == "LOSS")
    new_expired = sum(1 for t in new_trades if t["outcome"] == "EXPIRED")
    new_wr = (new_wins / new_total) * 100
    new_pnl = sum(t["pnl"] for t in new_trades)
    
    print(f"\n{'Metric':<25} {'OLD (BB-based)':<20} {'NEW (ATR-based)':<20} {'Change':<15}")
    print("-" * 80)
    print(f"{'Total Trades':<25} {old_total:<20} {new_total:<20}")
    print(f"{'Wins (T1 + T2)':<25} {old_wins:<20} {new_wins:<20} {'+' if new_wins > old_wins else ''}{new_wins - old_wins}")
    print(f"{'Losses':<25} {old_losses:<20} {new_losses:<20} {'+' if new_losses > old_losses else ''}{new_losses - old_losses}")
    print(f"{'Expired':<25} {old_expired:<20} {new_expired:<20} {'+' if new_expired > old_expired else ''}{new_expired - old_expired}")
    print("-" * 80)
    print(f"{'WIN RATE':<25} {old_wr:.1f}%{'':<16} {new_wr:.1f}%{'':<16} {'+' if new_wr > old_wr else ''}{new_wr - old_wr:.1f}%")
    print(f"{'Total P&L':<25} {old_pnl:+.2f}%{'':<14} {new_pnl:+.2f}%{'':<14} {'+' if new_pnl > old_pnl else ''}{new_pnl - old_pnl:.2f}%")
    
    # Detailed breakdown
    print(f"\n📊 BY DIRECTION (NEW Method):")
    new_longs = [t for t in new_trades if t["signal"] == "LONG"]
    new_shorts = [t for t in new_trades if t["signal"] == "SHORT"]
    
    if new_longs:
        long_wr = (sum(1 for t in new_longs if t["outcome"] in ["WIN_T1", "WIN_T2"]) / len(new_longs)) * 100
        print(f"   🟢 LONG: {len(new_longs)} trades | Win Rate: {long_wr:.1f}%")
    if new_shorts:
        short_wr = (sum(1 for t in new_shorts if t["outcome"] in ["WIN_T1", "WIN_T2"]) / len(new_shorts)) * 100
        print(f"   🔴 SHORT: {len(new_shorts)} trades | Win Rate: {short_wr:.1f}%")
    
    print(f"\n📊 BY CONFIRMATIONS (NEW Method):")
    for c in sorted(set(t["conf"] for t in new_trades)):
        ct = [t for t in new_trades if t["conf"] == c]
        cw = sum(1 for t in ct if t["outcome"] in ["WIN_T1", "WIN_T2"])
        c_wr = (cw / len(ct)) * 100
        print(f"   {c} conf: {len(ct)} trades | Win Rate: {c_wr:.1f}%")
    
    # Verdict
    print("\n" + "="*70)
    if new_wr > old_wr and new_pnl > old_pnl:
        print("✅ NEW METHOD IS BETTER! Higher win rate AND better P&L")
    elif new_wr > old_wr:
        print("✅ NEW METHOD has higher WIN RATE (but check P&L)")
    elif new_pnl > old_pnl:
        print("✅ NEW METHOD has better P&L (despite lower win rate)")
    else:
        print("⚠️ OLD METHOD performed better in this backtest")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_backtest()
