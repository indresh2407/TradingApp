"""
Today's Performance Check
Analyzes which stocks the strategy would have succeeded/failed on TODAY
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# NIFTY 50 stocks to analyze
STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "TITAN",
    "BAJFINANCE", "HCLTECH", "WIPRO", "SUNPHARMA", "ULTRACEMCO",
    "TATAMOTORS", "NTPC", "POWERGRID", "M&M", "ONGC",
    "JSWSTEEL", "TATASTEEL", "ADANIENT", "ADANIPORTS", "COALINDIA"
]


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI series"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_supertrend(high: pd.Series, low: pd.Series, close: pd.Series, 
                         period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """Calculate Supertrend - returns (supertrend_line, direction)"""
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


def analyze_today(symbol: str) -> Dict[str, Any]:
    """
    Analyze a stock for today's performance
    
    Returns signal given at market open and whether it would have been profitable
    """
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        
        # Get recent daily data for indicators
        hist_daily = ticker.history(period="1mo", interval="1d")
        if hist_daily.empty or len(hist_daily) < 15:
            return {"status": "error", "reason": "Insufficient daily data"}
        
        # Get today's intraday data (5-minute intervals)
        hist_intraday = ticker.history(period="1d", interval="5m")
        if hist_intraday.empty:
            return {"status": "error", "reason": "No intraday data (market closed?)"}
        
        # Calculate indicators on daily data (as of yesterday close)
        rsi = calculate_rsi(hist_daily['Close'])
        sma_5 = hist_daily['Close'].rolling(5).mean()
        sma_20 = hist_daily['Close'].rolling(20).mean()
        supertrend, st_direction = calculate_supertrend(hist_daily['High'], hist_daily['Low'], hist_daily['Close'])
        
        # Yesterday's values (signal generation point)
        prev_close = hist_daily['Close'].iloc[-2]
        prev_rsi = rsi.iloc[-2]
        prev_sma_5 = sma_5.iloc[-2]
        prev_sma_20 = sma_20.iloc[-2]
        prev_st_direction = st_direction.iloc[-2]  # 1 = bullish, -1 = bearish
        
        # Today's data
        today_open = hist_intraday['Open'].iloc[0]
        today_high = hist_intraday['High'].max()
        today_low = hist_intraday['Low'].min()
        today_close = hist_intraday['Close'].iloc[-1]
        current_price = today_close
        
        # Determine signal that would have been given at open
        signal = "NEUTRAL"
        signal_reason = []
        
        # LONG conditions
        long_score = 0
        if prev_close > prev_sma_20:
            long_score += 1
        if prev_rsi < 50:
            long_score += 1
        if prev_close > prev_sma_5:
            long_score += 1
        if prev_st_direction == 1:  # Supertrend bullish
            long_score += 3
            signal_reason.append("ST Bullish")
        
        # SHORT conditions
        short_score = 0
        if prev_close < prev_sma_20:
            short_score += 1
        if prev_rsi > 50:
            short_score += 1
        if prev_close < prev_sma_5:
            short_score += 1
        if prev_st_direction == -1:  # Supertrend bearish
            short_score += 3
            signal_reason.append("ST Bearish")
        
        if long_score >= 3 and long_score > short_score:
            signal = "LONG"
        elif short_score >= 3 and short_score > long_score:
            signal = "SHORT"
        
        # Calculate if trade would have been profitable
        # Entry at open, check if target (1%) hit before stoploss (0.7%)
        entry_price = today_open
        
        if signal == "LONG":
            stoploss = entry_price * 0.993  # 0.7% below
            target = entry_price * 1.01     # 1% above
            
            # Check intraday movement
            sl_hit = today_low <= stoploss
            target_hit = today_high >= target
            
            # Determine outcome
            if target_hit and not sl_hit:
                outcome = "WIN"
                pnl_pct = 1.0
            elif sl_hit and not target_hit:
                outcome = "LOSS"
                pnl_pct = -0.7
            elif target_hit and sl_hit:
                # Both hit - need to check which first (simplified: assume loss)
                outcome = "LOSS"
                pnl_pct = -0.7
            else:
                # Neither hit - use current price
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                outcome = "WIN" if pnl_pct > 0 else "LOSS"
                
        elif signal == "SHORT":
            stoploss = entry_price * 1.007  # 0.7% above
            target = entry_price * 0.99     # 1% below
            
            sl_hit = today_high >= stoploss
            target_hit = today_low <= target
            
            if target_hit and not sl_hit:
                outcome = "WIN"
                pnl_pct = 1.0
            elif sl_hit and not target_hit:
                outcome = "LOSS"
                pnl_pct = -0.7
            elif target_hit and sl_hit:
                outcome = "LOSS"
                pnl_pct = -0.7
            else:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
                outcome = "WIN" if pnl_pct > 0 else "LOSS"
        else:
            outcome = "NO_TRADE"
            pnl_pct = 0
        
        # Today's change
        today_change_pct = ((today_close - prev_close) / prev_close) * 100
        
        return {
            "status": "success",
            "symbol": symbol,
            "signal": signal,
            "signal_reason": " | ".join(signal_reason) if signal_reason else "Score-based",
            "supertrend": "BULLISH" if prev_st_direction == 1 else "BEARISH",
            "entry_price": round(entry_price, 2),
            "current_price": round(current_price, 2),
            "today_high": round(today_high, 2),
            "today_low": round(today_low, 2),
            "today_change_pct": round(today_change_pct, 2),
            "outcome": outcome,
            "pnl_pct": round(pnl_pct, 2),
            "rsi": round(prev_rsi, 1)
        }
        
    except Exception as e:
        return {"status": "error", "symbol": symbol, "reason": str(e)}


def run_today_analysis():
    """Run analysis for all stocks"""
    print("=" * 80)
    print(f"📊 TODAY'S STRATEGY PERFORMANCE CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    print(f"Analyzing {len(STOCKS)} NIFTY stocks...")
    print("-" * 80)
    
    results = []
    wins = []
    losses = []
    no_trades = []
    errors = []
    
    for i, symbol in enumerate(STOCKS):
        print(f"[{i+1}/{len(STOCKS)}] Analyzing {symbol}...", end=" ")
        result = analyze_today(symbol)
        
        if result.get("status") == "success":
            results.append(result)
            if result["outcome"] == "WIN":
                wins.append(result)
                print(f"✅ {result['signal']} → WIN ({result['pnl_pct']:+.2f}%)")
            elif result["outcome"] == "LOSS":
                losses.append(result)
                print(f"❌ {result['signal']} → LOSS ({result['pnl_pct']:+.2f}%)")
            else:
                no_trades.append(result)
                print(f"⏸️ NO TRADE")
        else:
            errors.append(result)
            print(f"⚠️ Error: {result.get('reason', 'Unknown')}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    
    total_trades = len(wins) + len(losses)
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    
    print(f"\n📊 Overall Stats:")
    print(f"   Total Signals: {total_trades}")
    print(f"   ✅ Wins: {len(wins)}")
    print(f"   ❌ Losses: {len(losses)}")
    print(f"   ⏸️ No Trade: {len(no_trades)}")
    print(f"   📈 Win Rate: {win_rate:.1f}%")
    
    if wins:
        total_profit = sum(w['pnl_pct'] for w in wins)
        print(f"\n✅ WINNING TRADES ({len(wins)}):")
        for w in wins:
            print(f"   {w['symbol']:12} | {w['signal']:5} | ST: {w['supertrend']:8} | Entry: ₹{w['entry_price']:,.2f} | P&L: {w['pnl_pct']:+.2f}%")
        print(f"   Total Profit: {total_profit:+.2f}%")
    
    if losses:
        total_loss = sum(l['pnl_pct'] for l in losses)
        print(f"\n❌ FAILED TRADES ({len(losses)}):")
        print("-" * 80)
        for l in losses:
            print(f"   {l['symbol']:12} | {l['signal']:5} | ST: {l['supertrend']:8} | Entry: ₹{l['entry_price']:,.2f} | P&L: {l['pnl_pct']:+.2f}%")
            print(f"      Reason: {l['signal_reason']} | RSI: {l['rsi']} | Day Move: {l['today_change_pct']:+.2f}%")
            
            # Failure analysis
            if l['signal'] == "LONG" and l['today_change_pct'] < 0:
                print(f"      ⚠️ LONG trade but stock fell {l['today_change_pct']:.2f}%")
            elif l['signal'] == "SHORT" and l['today_change_pct'] > 0:
                print(f"      ⚠️ SHORT trade but stock rose {l['today_change_pct']:.2f}%")
            print()
        print(f"   Total Loss: {total_loss:.2f}%")
    
    # Net P&L
    if total_trades > 0:
        net_pnl = sum(r['pnl_pct'] for r in results if r['outcome'] in ['WIN', 'LOSS'])
        print(f"\n💰 NET P&L: {net_pnl:+.2f}%")
    
    # Analysis of failures
    if losses:
        print("\n" + "=" * 80)
        print("🔍 FAILURE ANALYSIS")
        print("=" * 80)
        
        # Count failures by signal type
        long_losses = [l for l in losses if l['signal'] == 'LONG']
        short_losses = [l for l in losses if l['signal'] == 'SHORT']
        
        print(f"\n   LONG failures: {len(long_losses)}")
        print(f"   SHORT failures: {len(short_losses)}")
        
        # Check if Supertrend was correct
        st_wrong = [l for l in losses if 
                    (l['signal'] == 'LONG' and l['supertrend'] == 'BEARISH') or
                    (l['signal'] == 'SHORT' and l['supertrend'] == 'BULLISH')]
        
        st_right_but_failed = [l for l in losses if 
                               (l['signal'] == 'LONG' and l['supertrend'] == 'BULLISH') or
                               (l['signal'] == 'SHORT' and l['supertrend'] == 'BEARISH')]
        
        print(f"\n   Supertrend aligned but still failed: {len(st_right_but_failed)}")
        print(f"   Supertrend misaligned (shouldn't have traded): {len(st_wrong)}")
        
        if st_wrong:
            print("\n   ⚠️ These trades went AGAINST Supertrend (should have been filtered):")
            for s in st_wrong:
                print(f"      {s['symbol']}: {s['signal']} but ST was {s['supertrend']}")
    
    print("\n" + "=" * 80)
    
    return {
        "wins": wins,
        "losses": losses,
        "no_trades": no_trades,
        "win_rate": win_rate
    }


if __name__ == "__main__":
    run_today_analysis()
