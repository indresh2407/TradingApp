#!/usr/bin/env python3
"""
SIDDHI DayTrade Strategy Backtest v2
=====================================
Backtests the complete multi-timeframe strategy with advanced indicators:
- Core: VWAP, Supertrend, Bollinger Bands (5m + 10m)
- Advanced: ADX (7,7), ROC, BB Squeeze/Walk/Curl, VWAP Distance

Run locally: python3 backtest_daytrade_v2.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import warnings
warnings.filterwarnings('ignore')

# ============== INDICATOR CALCULATIONS ==============

def calculate_vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> Dict:
    """Calculate VWAP with signal"""
    typical_price = (high + low + close) / 3
    cumulative_tp_vol = (typical_price * volume).cumsum()
    cumulative_vol = volume.cumsum()
    vwap = cumulative_tp_vol / cumulative_vol
    
    current_vwap = vwap.iloc[-1]
    current_price = close.iloc[-1]
    distance_pct = ((current_price - current_vwap) / current_vwap) * 100
    
    if current_price > current_vwap * 1.002:
        signal = "BULLISH"
    elif current_price < current_vwap * 0.998:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"
    
    return {"vwap": current_vwap, "signal": signal, "distance_pct": distance_pct}


def calculate_supertrend(high: pd.Series, low: pd.Series, close: pd.Series, 
                         period: int = 10, multiplier: float = 3.0) -> Dict:
    """Calculate Supertrend indicator"""
    hl2 = (high + low) / 2
    
    # ATR
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    # Basic bands
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    # Supertrend
    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)
    
    for i in range(period, len(close)):
        if close.iloc[i] > upper_band.iloc[i-1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1] if i > period else 1
            
        if direction.iloc[i] == 1:
            supertrend.iloc[i] = lower_band.iloc[i]
        else:
            supertrend.iloc[i] = upper_band.iloc[i]
    
    current_dir = direction.iloc[-1]
    prev_dir = direction.iloc[-2] if len(direction) > 1 else current_dir
    crossover = current_dir != prev_dir
    
    signal = "BULLISH" if current_dir == 1 else "BEARISH"
    
    return {"value": supertrend.iloc[-1], "signal": signal, "crossover": crossover}


def calculate_bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> Dict:
    """Calculate Bollinger Bands with advanced signals"""
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    
    current_price = close.iloc[-1]
    prev_price = close.iloc[-2] if len(close) > 1 else current_price
    
    current_middle = middle.iloc[-1]
    current_upper = upper.iloc[-1]
    current_lower = lower.iloc[-1]
    
    # Bandwidth for squeeze detection
    bandwidth = (current_upper - current_lower) / current_middle * 100
    prev_bandwidth = (upper.iloc[-5] - lower.iloc[-5]) / middle.iloc[-5] * 100 if len(upper) > 5 else bandwidth
    squeeze = bandwidth < prev_bandwidth * 0.8
    
    # Percent B
    percent_b = ((current_price - current_lower) / (current_upper - current_lower)) * 100 if (current_upper - current_lower) > 0 else 50
    prev_percent_b = ((prev_price - lower.iloc[-2]) / (upper.iloc[-2] - lower.iloc[-2])) * 100 if len(upper) > 1 else 50
    
    # Walking and curling
    walking_upper = percent_b > 80 and close.tail(3).min() > middle.iloc[-3:].max()
    walking_lower = percent_b < 20 and close.tail(3).max() < middle.iloc[-3:].min()
    curling_down = prev_percent_b > 70 and percent_b < prev_percent_b and percent_b < 70
    curling_up = prev_percent_b < 30 and percent_b > prev_percent_b and percent_b > 30
    
    # Signal
    if percent_b > 100:
        signal = "OVERBOUGHT"
    elif percent_b < 0:
        signal = "OVERSOLD"
    elif percent_b > 80:
        signal = "BULLISH"
    elif percent_b < 20:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"
    
    return {
        "upper": current_upper, "lower": current_lower, "middle": current_middle,
        "signal": signal, "squeeze": squeeze, "percent_b": percent_b,
        "walking_upper": walking_upper, "walking_lower": walking_lower,
        "curling_down": curling_down, "curling_up": curling_up
    }


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, 
                  di_length: int = 7, adx_smoothing: int = 7) -> Dict:
    """Calculate ADX with DI Length=7, ADX Smoothing=7"""
    if len(close) < di_length + adx_smoothing + 5:
        return {"adx": 0, "trend_strength": "WEAK", "weakening": False, "plus_di": 0, "minus_di": 0, "trend_direction": "NEUTRAL"}
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=di_length).mean()
    
    # +DM and -DM
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
    
    current_adx = adx.iloc[-1] if not adx.empty else 0
    prev_adx = adx.iloc[-2] if len(adx) > 1 else current_adx
    
    if current_adx >= 40:
        trend_strength = "VERY_STRONG"
    elif current_adx >= 25:
        trend_strength = "STRONG"
    elif current_adx >= 20:
        trend_strength = "MODERATE"
    else:
        trend_strength = "WEAK"
    
    weakening = current_adx < prev_adx and current_adx > 20
    trend_direction = "BULLISH" if plus_di.iloc[-1] > minus_di.iloc[-1] else "BEARISH"
    
    return {
        "adx": current_adx, "trend_strength": trend_strength, "weakening": weakening,
        "plus_di": plus_di.iloc[-1], "minus_di": minus_di.iloc[-1], "trend_direction": trend_direction
    }


def calculate_roc(prices: pd.Series, period: int = 10) -> Dict:
    """Calculate Rate of Change with divergence detection"""
    if len(prices) < period + 5:
        return {"roc": 0, "signal": "NEUTRAL", "bearish_divergence": False, "bullish_divergence": False, "weakening": False}
    
    roc = ((prices.iloc[-1] - prices.iloc[-period]) / prices.iloc[-period]) * 100
    prev_roc = ((prices.iloc[-2] - prices.iloc[-period-1]) / prices.iloc[-period-1]) * 100
    
    # Divergence detection
    price_higher = prices.iloc[-1] > prices.iloc[-5:-1].max()
    roc_lower = roc < prev_roc
    bearish_divergence = price_higher and roc_lower and roc > 0
    
    price_lower = prices.iloc[-1] < prices.iloc[-5:-1].min()
    roc_higher = roc > prev_roc
    bullish_divergence = price_lower and roc_higher and roc < 0
    
    weakening = abs(roc) < abs(prev_roc)
    
    if roc > 2:
        signal = "BULLISH"
    elif roc < -2:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"
    
    return {
        "roc": roc, "signal": signal, "bearish_divergence": bearish_divergence,
        "bullish_divergence": bullish_divergence, "weakening": weakening
    }


def calculate_vwap_distance(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> Dict:
    """Calculate VWAP with standard deviation bands (rubber band effect)"""
    if len(close) < 20:
        return {"overextended_up": False, "overextended_down": False, "extreme_up": False, "extreme_down": False}
    
    typical_price = (high + low + close) / 3
    cumulative_tp_vol = (typical_price * volume).cumsum()
    cumulative_vol = volume.cumsum()
    vwap = cumulative_tp_vol / cumulative_vol
    
    current_vwap = vwap.iloc[-1]
    current_price = close.iloc[-1]
    
    squared_diff = ((typical_price - vwap) ** 2 * volume).cumsum()
    variance = squared_diff / cumulative_vol
    vwap_std = variance ** 0.5
    current_std = vwap_std.iloc[-1]
    
    band_2_upper = current_vwap + 2 * current_std
    band_2_lower = current_vwap - 2 * current_std
    band_3_upper = current_vwap + 3 * current_std
    band_3_lower = current_vwap - 3 * current_std
    
    return {
        "overextended_up": current_price >= band_2_upper,
        "overextended_down": current_price <= band_2_lower,
        "extreme_up": current_price >= band_3_upper,
        "extreme_down": current_price <= band_3_lower
    }


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    """Calculate ATR"""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr.iloc[-1] if not atr.empty else 0


# ============== STRATEGY ANALYSIS ==============

def analyze_for_signal(hist_5m: pd.DataFrame, hist_10m: pd.DataFrame, min_confirmations: int = 4) -> Dict:
    """
    Analyze stock data and return signal using the DayTrade strategy
    """
    if hist_5m.empty or len(hist_5m) < 50 or hist_10m.empty or len(hist_10m) < 20:
        return {"signal": "NONE", "confirmations": 0}
    
    ltp = hist_5m['Close'].iloc[-1]
    
    # 5-MINUTE ANALYSIS
    vwap_5m = calculate_vwap(hist_5m['High'], hist_5m['Low'], hist_5m['Close'], hist_5m['Volume'])
    st_5m = calculate_supertrend(hist_5m['High'], hist_5m['Low'], hist_5m['Close'])
    bb_5m = calculate_bollinger_bands(hist_5m['Close'])
    
    # 10-MINUTE ANALYSIS
    vwap_10m = calculate_vwap(hist_10m['High'], hist_10m['Low'], hist_10m['Close'], hist_10m['Volume'])
    st_10m = calculate_supertrend(hist_10m['High'], hist_10m['Low'], hist_10m['Close'])
    bb_10m = calculate_bollinger_bands(hist_10m['Close'])
    
    # ADVANCED INDICATORS
    adx_data = calculate_adx(hist_5m['High'], hist_5m['Low'], hist_5m['Close'], di_length=7, adx_smoothing=7)
    roc_data = calculate_roc(hist_5m['Close'], period=10)
    vwap_dist = calculate_vwap_distance(hist_5m['High'], hist_5m['Low'], hist_5m['Close'], hist_5m['Volume'])
    
    atr = calculate_atr(hist_5m['High'], hist_5m['Low'], hist_5m['Close'])
    
    # LONG CONFIRMATION
    long_conf = 0
    
    if vwap_5m["signal"] == "BULLISH": long_conf += 1
    if st_5m["signal"] == "BULLISH":
        long_conf += 1
        if st_5m["crossover"]: long_conf += 1
    if bb_5m["signal"] in ["OVERSOLD", "BULLISH"]: long_conf += 1
    
    if vwap_10m["signal"] == "BULLISH": long_conf += 1
    if st_10m["signal"] == "BULLISH":
        long_conf += 1
        if st_10m["crossover"]: long_conf += 1
    if bb_10m["signal"] in ["OVERSOLD", "BULLISH"]: long_conf += 1
    
    # Advanced long confirmations
    if adx_data["adx"] >= 25 and adx_data["trend_direction"] == "BULLISH":
        long_conf += 1
    if roc_data["signal"] == "BULLISH" and not roc_data["weakening"]:
        long_conf += 1
    if roc_data["bullish_divergence"]:
        long_conf += 2
    if bb_5m["squeeze"] and st_5m["signal"] == "BULLISH":
        long_conf += 1
    if bb_5m["curling_up"]:
        long_conf += 1
    if vwap_dist["overextended_down"] and st_5m["signal"] == "BULLISH":
        long_conf += 1
    
    # Long warnings (reduce confidence)
    if adx_data["weakening"] and adx_data["trend_direction"] == "BULLISH":
        long_conf -= 1
    if roc_data["bearish_divergence"]:
        long_conf -= 2
    if bb_5m["walking_upper"] and bb_5m["curling_down"]:
        long_conf -= 1
    if vwap_dist["overextended_up"] or vwap_dist["extreme_up"]:
        long_conf -= 1
    
    # SHORT CONFIRMATION
    short_conf = 0
    
    if vwap_5m["signal"] == "BEARISH": short_conf += 1
    if st_5m["signal"] == "BEARISH":
        short_conf += 1
        if st_5m["crossover"]: short_conf += 1
    if bb_5m["signal"] in ["OVERBOUGHT", "BEARISH"]: short_conf += 1
    
    if vwap_10m["signal"] == "BEARISH": short_conf += 1
    if st_10m["signal"] == "BEARISH":
        short_conf += 1
        if st_10m["crossover"]: short_conf += 1
    if bb_10m["signal"] in ["OVERBOUGHT", "BEARISH"]: short_conf += 1
    
    # Advanced short confirmations
    if adx_data["adx"] >= 25 and adx_data["trend_direction"] == "BEARISH":
        short_conf += 1
    if roc_data["signal"] == "BEARISH" and not roc_data["weakening"]:
        short_conf += 1
    if roc_data["bearish_divergence"]:
        short_conf += 2
    if bb_5m["squeeze"] and st_5m["signal"] == "BEARISH":
        short_conf += 1
    if bb_5m["curling_down"]:
        short_conf += 1
    if vwap_dist["overextended_up"] and st_5m["signal"] == "BEARISH":
        short_conf += 1
    
    # Short warnings
    if adx_data["weakening"] and adx_data["trend_direction"] == "BEARISH":
        short_conf -= 1
    if roc_data["bullish_divergence"]:
        short_conf -= 2
    if bb_5m["walking_lower"] and bb_5m["curling_up"]:
        short_conf -= 1
    if vwap_dist["overextended_down"] or vwap_dist["extreme_down"]:
        short_conf -= 1
    
    # Determine signal
    if long_conf >= min_confirmations and long_conf > short_conf:
        entry = ltp
        stoploss = max(bb_5m["lower"] * 0.998, st_5m["value"] * 0.995)
        target1 = min(bb_5m["upper"], ltp * 1.015)
        target2 = bb_5m["upper"] * 1.01
        
        if stoploss >= entry:
            stoploss = entry * 0.993
        if target1 <= entry:
            target1 = entry * 1.01
        
        return {
            "signal": "LONG",
            "confirmations": long_conf,
            "entry": entry,
            "stoploss": stoploss,
            "target1": target1,
            "target2": target2,
            "atr": atr
        }
    
    elif short_conf >= min_confirmations and short_conf > long_conf:
        entry = ltp
        stoploss = min(bb_5m["upper"] * 1.002, st_5m["value"] * 1.005)
        target1 = max(bb_5m["lower"], ltp * 0.985)
        target2 = bb_5m["lower"] * 0.99
        
        if stoploss <= entry:
            stoploss = entry * 1.007
        if target1 >= entry:
            target1 = entry * 0.99
        
        return {
            "signal": "SHORT",
            "confirmations": short_conf,
            "entry": entry,
            "stoploss": stoploss,
            "target1": target1,
            "target2": target2,
            "atr": atr
        }
    
    return {"signal": "NONE", "confirmations": max(long_conf, short_conf)}


def check_trade_outcome(hist_5m: pd.DataFrame, signal: Dict, entry_idx: int, 
                        max_candles: int = 36) -> Dict:
    """
    Check if trade hit target or stoploss within max_candles (36 = ~3 hours on 5m)
    """
    if signal["signal"] == "NONE":
        return {"outcome": "NO_SIGNAL"}
    
    entry = signal["entry"]
    stoploss = signal["stoploss"]
    target1 = signal["target1"]
    target2 = signal["target2"]
    
    end_idx = min(entry_idx + max_candles, len(hist_5m))
    future_data = hist_5m.iloc[entry_idx:end_idx]
    
    if future_data.empty:
        return {"outcome": "NO_DATA"}
    
    for i, (idx, row) in enumerate(future_data.iterrows()):
        high = row['High']
        low = row['Low']
        close = row['Close']
        
        if signal["signal"] == "LONG":
            # Check stoploss first
            if low <= stoploss:
                loss_pct = ((stoploss - entry) / entry) * 100
                return {
                    "outcome": "LOSS",
                    "exit_price": stoploss,
                    "pnl_pct": loss_pct,
                    "candles": i + 1,
                    "time_mins": (i + 1) * 5
                }
            # Check target2
            if high >= target2:
                profit_pct = ((target2 - entry) / entry) * 100
                return {
                    "outcome": "WIN_T2",
                    "exit_price": target2,
                    "pnl_pct": profit_pct,
                    "candles": i + 1,
                    "time_mins": (i + 1) * 5
                }
            # Check target1
            if high >= target1:
                profit_pct = ((target1 - entry) / entry) * 100
                return {
                    "outcome": "WIN_T1",
                    "exit_price": target1,
                    "pnl_pct": profit_pct,
                    "candles": i + 1,
                    "time_mins": (i + 1) * 5
                }
        
        else:  # SHORT
            # Check stoploss first
            if high >= stoploss:
                loss_pct = ((entry - stoploss) / entry) * 100
                return {
                    "outcome": "LOSS",
                    "exit_price": stoploss,
                    "pnl_pct": loss_pct,
                    "candles": i + 1,
                    "time_mins": (i + 1) * 5
                }
            # Check target2
            if low <= target2:
                profit_pct = ((entry - target2) / entry) * 100
                return {
                    "outcome": "WIN_T2",
                    "exit_price": target2,
                    "pnl_pct": profit_pct,
                    "candles": i + 1,
                    "time_mins": (i + 1) * 5
                }
            # Check target1
            if low <= target1:
                profit_pct = ((entry - target1) / entry) * 100
                return {
                    "outcome": "WIN_T1",
                    "exit_price": target1,
                    "pnl_pct": profit_pct,
                    "candles": i + 1,
                    "time_mins": (i + 1) * 5
                }
    
    # Time expired - exit at last close
    final_close = future_data['Close'].iloc[-1]
    if signal["signal"] == "LONG":
        pnl_pct = ((final_close - entry) / entry) * 100
    else:
        pnl_pct = ((entry - final_close) / entry) * 100
    
    return {
        "outcome": "EXPIRED",
        "exit_price": final_close,
        "pnl_pct": pnl_pct,
        "candles": len(future_data),
        "time_mins": len(future_data) * 5
    }


# ============== BACKTEST RUNNER ==============

def run_backtest(stocks: List[str], days: int = 5, signals_per_day: int = 3):
    """
    Run backtest on given stocks
    """
    print("\n" + "="*70)
    print("🚀 SIDDHI DayTrade Strategy Backtest v2")
    print("="*70)
    print(f"📊 Stocks: {len(stocks)}")
    print(f"📅 Days: {days}")
    print(f"🎯 Strategy: Multi-TF (5m+10m) + ADX(7,7) + ROC + BB Advanced + VWAP Distance")
    print("="*70 + "\n")
    
    all_trades = []
    stock_stats = {}
    
    for symbol in stocks:
        yahoo_symbol = f"{symbol}.NS"
        print(f"\n📈 Analyzing {symbol}...", end=" ")
        
        try:
            ticker = yf.Ticker(yahoo_symbol)
            hist_5m = ticker.history(period=f"{days+2}d", interval="5m")
            
            if hist_5m.empty or len(hist_5m) < 100:
                print("❌ Insufficient data")
                continue
            
            # Resample to 10m
            hist_10m = hist_5m.resample('10min').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min',
                'Close': 'last', 'Volume': 'sum'
            }).dropna()
            
            stock_trades = []
            
            # Analyze at different times of day (9:30, 10:30, 11:30, 13:00, 14:00)
            analysis_times = [15, 27, 39, 57, 69]  # Candles from market open (9:15)
            
            # Group by date
            if hist_5m.index.tz is not None:
                dates = hist_5m.index.tz_localize(None).date
            else:
                dates = hist_5m.index.date
            
            unique_dates = pd.Series(dates).unique()[-days:]
            
            for date in unique_dates:
                day_mask = dates == date
                day_indices = np.where(day_mask)[0]
                
                if len(day_indices) < 75:  # Need full day
                    continue
                
                signals_today = 0
                
                for candle_offset in analysis_times:
                    if signals_today >= signals_per_day:
                        break
                    
                    analysis_idx = day_indices[0] + candle_offset
                    if analysis_idx >= len(hist_5m) - 36:  # Need future data
                        continue
                    
                    # Get data up to analysis point
                    hist_5m_slice = hist_5m.iloc[:analysis_idx+1]
                    hist_10m_slice = hist_10m[hist_10m.index <= hist_5m.index[analysis_idx]]
                    
                    if len(hist_5m_slice) < 50 or len(hist_10m_slice) < 20:
                        continue
                    
                    # Analyze
                    signal = analyze_for_signal(hist_5m_slice, hist_10m_slice)
                    
                    if signal["signal"] != "NONE":
                        # Check outcome
                        outcome = check_trade_outcome(hist_5m, signal, analysis_idx)
                        
                        trade = {
                            "symbol": symbol,
                            "date": str(date),
                            "signal": signal["signal"],
                            "confirmations": signal["confirmations"],
                            "entry": signal["entry"],
                            "stoploss": signal["stoploss"],
                            "target1": signal["target1"],
                            "outcome": outcome["outcome"],
                            "pnl_pct": outcome.get("pnl_pct", 0),
                            "time_mins": outcome.get("time_mins", 0)
                        }
                        
                        stock_trades.append(trade)
                        all_trades.append(trade)
                        signals_today += 1
            
            if stock_trades:
                wins = sum(1 for t in stock_trades if t["outcome"] in ["WIN_T1", "WIN_T2"])
                losses = sum(1 for t in stock_trades if t["outcome"] == "LOSS")
                total_pnl = sum(t["pnl_pct"] for t in stock_trades)
                
                stock_stats[symbol] = {
                    "trades": len(stock_trades),
                    "wins": wins,
                    "losses": losses,
                    "win_rate": (wins / len(stock_trades) * 100) if stock_trades else 0,
                    "total_pnl": total_pnl
                }
                print(f"✅ {len(stock_trades)} trades | Win Rate: {stock_stats[symbol]['win_rate']:.1f}% | P&L: {total_pnl:+.2f}%")
            else:
                print("⚪ No signals")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    # ============== RESULTS SUMMARY ==============
    print("\n" + "="*70)
    print("📊 BACKTEST RESULTS SUMMARY")
    print("="*70)
    
    if not all_trades:
        print("❌ No trades generated during backtest period")
        return
    
    total_trades = len(all_trades)
    wins_t1 = sum(1 for t in all_trades if t["outcome"] == "WIN_T1")
    wins_t2 = sum(1 for t in all_trades if t["outcome"] == "WIN_T2")
    losses = sum(1 for t in all_trades if t["outcome"] == "LOSS")
    expired = sum(1 for t in all_trades if t["outcome"] == "EXPIRED")
    
    total_wins = wins_t1 + wins_t2
    win_rate = (total_wins / total_trades) * 100
    
    total_pnl = sum(t["pnl_pct"] for t in all_trades)
    avg_win = np.mean([t["pnl_pct"] for t in all_trades if t["outcome"] in ["WIN_T1", "WIN_T2"]]) if total_wins > 0 else 0
    avg_loss = np.mean([t["pnl_pct"] for t in all_trades if t["outcome"] == "LOSS"]) if losses > 0 else 0
    
    long_trades = [t for t in all_trades if t["signal"] == "LONG"]
    short_trades = [t for t in all_trades if t["signal"] == "SHORT"]
    
    long_win_rate = (sum(1 for t in long_trades if t["outcome"] in ["WIN_T1", "WIN_T2"]) / len(long_trades) * 100) if long_trades else 0
    short_win_rate = (sum(1 for t in short_trades if t["outcome"] in ["WIN_T1", "WIN_T2"]) / len(short_trades) * 100) if short_trades else 0
    
    profit_factor = abs(sum(t["pnl_pct"] for t in all_trades if t["pnl_pct"] > 0) / sum(t["pnl_pct"] for t in all_trades if t["pnl_pct"] < 0)) if sum(t["pnl_pct"] for t in all_trades if t["pnl_pct"] < 0) != 0 else 0
    
    print(f"\n📈 OVERALL PERFORMANCE:")
    print(f"   Total Trades: {total_trades}")
    print(f"   ✅ Wins (T1): {wins_t1} | Wins (T2): {wins_t2} | Total Wins: {total_wins}")
    print(f"   ❌ Losses: {losses}")
    print(f"   ⏰ Expired: {expired}")
    print(f"   🎯 Win Rate: {win_rate:.1f}%")
    print(f"   💰 Total P&L: {total_pnl:+.2f}%")
    print(f"   📊 Avg Win: {avg_win:+.2f}% | Avg Loss: {avg_loss:.2f}%")
    print(f"   📈 Profit Factor: {profit_factor:.2f}")
    
    print(f"\n📊 BY DIRECTION:")
    print(f"   🟢 LONG: {len(long_trades)} trades | Win Rate: {long_win_rate:.1f}%")
    print(f"   🔴 SHORT: {len(short_trades)} trades | Win Rate: {short_win_rate:.1f}%")
    
    # Confirmation breakdown
    print(f"\n📊 BY CONFIRMATIONS:")
    for conf in sorted(set(t["confirmations"] for t in all_trades)):
        conf_trades = [t for t in all_trades if t["confirmations"] == conf]
        conf_wins = sum(1 for t in conf_trades if t["outcome"] in ["WIN_T1", "WIN_T2"])
        conf_wr = (conf_wins / len(conf_trades) * 100) if conf_trades else 0
        print(f"   {conf} confirmations: {len(conf_trades)} trades | Win Rate: {conf_wr:.1f}%")
    
    # Top/Worst performers
    if stock_stats:
        print(f"\n🏆 TOP PERFORMERS:")
        sorted_stocks = sorted(stock_stats.items(), key=lambda x: x[1]["total_pnl"], reverse=True)
        for symbol, stats in sorted_stocks[:5]:
            print(f"   {symbol}: {stats['trades']} trades | WR: {stats['win_rate']:.1f}% | P&L: {stats['total_pnl']:+.2f}%")
        
        print(f"\n📉 WORST PERFORMERS:")
        for symbol, stats in sorted_stocks[-3:]:
            print(f"   {symbol}: {stats['trades']} trades | WR: {stats['win_rate']:.1f}% | P&L: {stats['total_pnl']:+.2f}%")
    
    print("\n" + "="*70)
    print("✅ Backtest Complete!")
    print("="*70 + "\n")


# ============== MAIN ==============

if __name__ == "__main__":
    # NIFTY 50 + Bank stocks
    STOCKS = [
        # NIFTY 50 Major
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "SBIN", "BHARTIARTL", "KOTAKBANK", "ITC",
        "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "HCLTECH",
        "SUNPHARMA", "TITAN", "ULTRACEMCO", "WIPRO", "BAJFINANCE",
        # Bank NIFTY
        "INDUSINDBK", "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "PNB",
        # IT
        "TECHM", "MPHASIS", "LTIM", "COFORGE",
        # Auto
        "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO",
        # Others
        "ADANIENT", "ADANIPORTS", "ONGC", "POWERGRID", "NTPC"
    ]
    
    # Run backtest for last 5 trading days
    run_backtest(STOCKS, days=5, signals_per_day=3)
