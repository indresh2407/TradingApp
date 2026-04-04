#!/usr/bin/env python3
"""
SIDDHI DayTrade Direction Accuracy Backtest
============================================
Measures if the stock moved in the PREDICTED DIRECTION, not just target hits.

Success = Stock moved in predicted direction (LONG→Up, SHORT→Down)

Run: python3 backtest_direction.py
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
    
    if lc >= min_conf and lc > sc:
        return {"signal": "LONG", "confirmations": lc, "entry": ltp}
    
    if sc >= min_conf and sc > lc:
        return {"signal": "SHORT", "confirmations": sc, "entry": ltp}
    
    return {"signal": "NONE", "confirmations": max(lc, sc)}


def check_direction_outcome(h5, sig, entry_idx, check_candles=12):
    """
    Check if the stock moved in the PREDICTED DIRECTION.
    
    For LONG: Did price go UP after entry? (max_high > entry)
    For SHORT: Did price go DOWN after entry? (min_low < entry)
    
    Also measures:
    - Max favorable move (how much it moved in our direction)
    - Max adverse move (how much it moved against us)
    """
    if sig["signal"] == "NONE":
        return {"direction_correct": None}
    
    entry = sig["entry"]
    future = h5.iloc[entry_idx:min(entry_idx + check_candles, len(h5))]
    
    if future.empty or len(future) < 2:
        return {"direction_correct": None}
    
    if sig["signal"] == "LONG":
        # For LONG: Success if price went UP
        max_high = future['High'].max()
        min_low = future['Low'].min()
        close_final = future['Close'].iloc[-1]
        
        # Max favorable move (upside)
        max_favorable = ((max_high - entry) / entry) * 100
        # Max adverse move (downside)
        max_adverse = ((entry - min_low) / entry) * 100
        # Final P&L
        final_pnl = ((close_final - entry) / entry) * 100
        
        # Direction correct if price moved up at least 0.1%
        direction_correct = max_favorable >= 0.1
        
        # Strong move = moved up more than down
        strong_move = max_favorable > max_adverse
        
    else:  # SHORT
        # For SHORT: Success if price went DOWN
        max_high = future['High'].max()
        min_low = future['Low'].min()
        close_final = future['Close'].iloc[-1]
        
        # Max favorable move (downside for shorts)
        max_favorable = ((entry - min_low) / entry) * 100
        # Max adverse move (upside for shorts)
        max_adverse = ((max_high - entry) / entry) * 100
        # Final P&L
        final_pnl = ((entry - close_final) / entry) * 100
        
        # Direction correct if price moved down at least 0.1%
        direction_correct = max_favorable >= 0.1
        
        # Strong move = moved down more than up
        strong_move = max_favorable > max_adverse
    
    return {
        "direction_correct": direction_correct,
        "strong_move": strong_move,
        "max_favorable": round(max_favorable, 2),
        "max_adverse": round(max_adverse, 2),
        "final_pnl": round(final_pnl, 2),
        "candles_checked": len(future)
    }


def run_backtest():
    print("\n" + "="*70)
    print("🎯 SIDDHI DayTrade DIRECTION ACCURACY Backtest")
    print("="*70)
    print(f"📊 Testing: {len(STOCKS)} stocks | Period: 5 days")
    print(f"🎯 Metric: Did stock move in PREDICTED DIRECTION?")
    print(f"⏱️  Check Window: 1 hour (12 candles on 5-min)")
    print("="*70)
    
    all_trades = []
    stock_results = {}
    
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
            
            trades = []
            for date in dates:
                day_mask = (h5.index.date if h5.index.tz is None else h5.index.tz_localize(None).date) == date
                day_idx = np.where(day_mask)[0]
                
                if len(day_idx) < 75:
                    continue
                
                # Test at multiple times: 9:30, 10:15, 11:00, 11:45, 12:30, 13:15, 14:00
                for offset in [15, 27, 39, 51, 63, 75, 87]:
                    idx = day_idx[0] + offset
                    if idx >= len(h5) - 12:  # Need 12 candles (1 hour) of future data
                        continue
                    
                    sig = analyze_signal(h5.iloc[:idx+1], h10[h10.index <= h5.index[idx]])
                    
                    if sig["signal"] != "NONE":
                        out = check_direction_outcome(h5, sig, idx, check_candles=12)
                        
                        if out["direction_correct"] is not None:
                            trade = {
                                "symbol": symbol,
                                "date": str(date),
                                "signal": sig["signal"],
                                "conf": sig["confirmations"],
                                "direction_correct": out["direction_correct"],
                                "strong_move": out["strong_move"],
                                "max_favorable": out["max_favorable"],
                                "max_adverse": out["max_adverse"],
                                "final_pnl": out["final_pnl"]
                            }
                            trades.append(trade)
                            all_trades.append(trade)
            
            if trades:
                correct = sum(1 for t in trades if t["direction_correct"])
                strong = sum(1 for t in trades if t["strong_move"])
                accuracy = (correct / len(trades)) * 100
                avg_fav = np.mean([t["max_favorable"] for t in trades])
                
                stock_results[symbol] = {
                    "trades": len(trades),
                    "correct": correct,
                    "accuracy": accuracy,
                    "avg_favorable": avg_fav
                }
                
                print(f"✅ {len(trades)} signals | Direction Accuracy: {accuracy:.0f}% | Avg Move: {avg_fav:.2f}%")
            else:
                print("⚪ No signals")
                
        except Exception as e:
            print(f"❌ {e}")
    
    # ============== SUMMARY ==============
    print("\n" + "="*70)
    print("📊 DIRECTION ACCURACY RESULTS")
    print("="*70)
    
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
    
    print(f"\n🎯 OVERALL DIRECTION ACCURACY: {accuracy:.1f}%")
    print(f"   Total Signals: {total}")
    print(f"   ✅ Correct Direction: {correct} ({accuracy:.1f}%)")
    print(f"   💪 Strong Moves (favorable > adverse): {strong} ({strong_rate:.1f}%)")
    print(f"\n📈 MOVE ANALYSIS:")
    print(f"   Avg Favorable Move: +{avg_favorable:.2f}%")
    print(f"   Avg Adverse Move: -{avg_adverse:.2f}%")
    print(f"   Avg Final P&L (at 1hr): {avg_pnl:+.2f}%")
    
    # By direction
    longs = [t for t in all_trades if t["signal"] == "LONG"]
    shorts = [t for t in all_trades if t["signal"] == "SHORT"]
    
    if longs:
        long_acc = (sum(1 for t in longs if t["direction_correct"]) / len(longs)) * 100
        long_fav = np.mean([t["max_favorable"] for t in longs])
    else:
        long_acc, long_fav = 0, 0
        
    if shorts:
        short_acc = (sum(1 for t in shorts if t["direction_correct"]) / len(shorts)) * 100
        short_fav = np.mean([t["max_favorable"] for t in shorts])
    else:
        short_acc, short_fav = 0, 0
    
    print(f"\n📊 BY DIRECTION:")
    print(f"   🟢 LONG:  {len(longs)} signals | Accuracy: {long_acc:.1f}% | Avg Up: +{long_fav:.2f}%")
    print(f"   🔴 SHORT: {len(shorts)} signals | Accuracy: {short_acc:.1f}% | Avg Down: +{short_fav:.2f}%")
    
    # By confirmations
    print(f"\n📊 BY CONFIRMATION COUNT:")
    for c in sorted(set(t["conf"] for t in all_trades)):
        ct = [t for t in all_trades if t["conf"] == c]
        c_correct = sum(1 for t in ct if t["direction_correct"])
        c_acc = (c_correct / len(ct)) * 100
        c_fav = np.mean([t["max_favorable"] for t in ct])
        print(f"   {c} confirmations: {len(ct)} signals | Accuracy: {c_acc:.1f}% | Avg Move: +{c_fav:.2f}%")
    
    # Top performers
    if stock_results:
        print(f"\n🏆 BEST STOCKS (by accuracy):")
        sorted_stocks = sorted(stock_results.items(), key=lambda x: x[1]["accuracy"], reverse=True)
        for sym, stats in sorted_stocks[:5]:
            print(f"   {sym}: {stats['accuracy']:.0f}% accuracy | {stats['trades']} signals | +{stats['avg_favorable']:.2f}% avg move")
        
        print(f"\n📉 WORST STOCKS:")
        for sym, stats in sorted_stocks[-3:]:
            print(f"   {sym}: {stats['accuracy']:.0f}% accuracy | {stats['trades']} signals")
    
    # Time-based analysis
    print(f"\n⏱️  Note: Direction checked over 1 hour (12 candles) after signal")
    print(f"   A 'correct' direction = stock moved at least 0.1% in predicted direction")
    print(f"   A 'strong move' = favorable move > adverse move")
    
    print("\n" + "="*70)
    print("✅ Backtest Complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_backtest()
