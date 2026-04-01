"""
Quick Analysis for LT Trade
User entry: 3680, Target: 3691
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

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

# User's trade details
ENTRY_PRICE = 3680
TARGET = 3691
STOP_LOSS = ENTRY_PRICE * 0.993  # 0.7% below

print("=" * 70)
print("📊 LT (LARSEN & TOUBRO) - TRADE ANALYSIS")
print("=" * 70)
print(f"\n💼 YOUR TRADE:")
print(f"   Entry: ₹{ENTRY_PRICE:,.2f}")
print(f"   Target: ₹{TARGET:,.2f} (+{((TARGET-ENTRY_PRICE)/ENTRY_PRICE)*100:.2f}%)")
print(f"   Stop Loss: ₹{STOP_LOSS:,.2f} (-0.7%)")
print("-" * 70)

try:
    ticker = yf.Ticker("LT.NS")
    
    # Get daily data
    daily = ticker.history(period="1mo", interval="1d")
    
    # Get 5-min intraday data
    intraday = ticker.history(period="5d", interval="5m")
    
    if intraday.empty:
        print("⚠️ Market might be closed. Using last available data.")
        intraday = daily
    
    # Current price
    current_price = intraday['Close'].iloc[-1]
    today_high = intraday['High'].iloc[-1] if len(intraday) < 50 else intraday.tail(50)['High'].max()
    today_low = intraday['Low'].iloc[-1] if len(intraday) < 50 else intraday.tail(50)['Low'].min()
    
    # Calculate P&L
    pnl = current_price - ENTRY_PRICE
    pnl_pct = (pnl / ENTRY_PRICE) * 100
    
    print(f"\n📈 CURRENT STATUS:")
    print(f"   Current Price: ₹{current_price:,.2f}")
    print(f"   Today's High: ₹{today_high:,.2f}")
    print(f"   Today's Low: ₹{today_low:,.2f}")
    print(f"   Your P&L: ₹{pnl:,.2f} ({pnl_pct:+.2f}%)")
    
    if pnl >= 0:
        print(f"   Status: 🟢 IN PROFIT")
    else:
        print(f"   Status: 🔴 IN LOSS")
    
    # Did target get hit?
    if today_high >= TARGET:
        print(f"\n   ✅ TARGET WAS HIT! High reached ₹{today_high:,.2f}")
    else:
        print(f"\n   ❌ Target NOT hit yet. Need ₹{TARGET - current_price:,.2f} more")
    
    # Did stop loss get hit?
    if today_low <= STOP_LOSS:
        print(f"   ⚠️ STOP LOSS WAS HIT! Low was ₹{today_low:,.2f}")
    
    # Calculate indicators
    print("\n" + "-" * 70)
    print("📊 TECHNICAL ANALYSIS:")
    
    # RSI
    rsi = calculate_rsi(daily['Close']).iloc[-1]
    print(f"\n   RSI (14): {rsi:.1f}", end="")
    if rsi > 70:
        print(" - ⚠️ OVERBOUGHT (risky for longs)")
    elif rsi < 30:
        print(" - 🟢 OVERSOLD (good for longs)")
    else:
        print(" - Neutral")
    
    # Supertrend on 5-min data
    if len(intraday) >= 20:
        st, st_dir = calculate_supertrend(intraday['High'], intraday['Low'], intraday['Close'])
        st_value = st.iloc[-1]
        st_direction = st_dir.iloc[-1]
        st_signal = "BULLISH 🟢" if st_direction == 1 else "BEARISH 🔴"
        
        print(f"\n   Supertrend (5-min): {st_signal}")
        print(f"   ST Value: ₹{st_value:,.2f}")
        
        if st_direction == 1:
            print(f"   → Price is ABOVE Supertrend - Trend supports LONG")
        else:
            print(f"   → Price is BELOW Supertrend - ⚠️ Trend turned BEARISH!")
    
    # Daily trend
    sma_5 = daily['Close'].rolling(5).mean().iloc[-1]
    sma_20 = daily['Close'].rolling(20).mean().iloc[-1]
    
    print(f"\n   SMA 5: ₹{sma_5:,.2f}")
    print(f"   SMA 20: ₹{sma_20:,.2f}")
    
    if current_price > sma_5 > sma_20:
        print("   → Strong Uptrend ✅")
    elif current_price < sma_5 < sma_20:
        print("   → Strong Downtrend ❌")
    else:
        print("   → Mixed/Sideways trend")
    
    # What went wrong?
    print("\n" + "=" * 70)
    print("🔍 ANALYSIS - WHAT HAPPENED:")
    print("=" * 70)
    
    issues = []
    
    # Check if Supertrend was bearish at entry
    if len(intraday) >= 20 and st_direction == -1:
        issues.append("⚠️ Supertrend turned BEARISH - trend reversed against your trade")
    
    # Check if RSI was overbought
    if rsi > 65:
        issues.append(f"⚠️ RSI is high ({rsi:.0f}) - stock may have been overbought")
    
    # Check if price is below entry
    if current_price < ENTRY_PRICE:
        drop_pct = ((ENTRY_PRICE - current_price) / ENTRY_PRICE) * 100
        issues.append(f"⚠️ Price dropped {drop_pct:.2f}% from your entry")
    
    # Check if near day low
    day_range = today_high - today_low
    if day_range > 0:
        position = (current_price - today_low) / day_range
        if position < 0.3:
            issues.append("⚠️ Price is near day's LOW - weak intraday momentum")
    
    if issues:
        print("\nPossible reasons for loss:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n   No major issues detected. Market volatility may be the cause.")
    
    # Recommendation
    print("\n" + "=" * 70)
    print("💡 RECOMMENDATION:")
    print("=" * 70)
    
    if current_price < STOP_LOSS:
        print("\n   🛑 EXIT - Stop loss breached. Cut your loss.")
    elif len(intraday) >= 20 and st_direction == -1:
        print("\n   ⚠️ CAUTION - Supertrend is BEARISH")
        print("   Options:")
        print("   1. Exit if loss exceeds your risk tolerance")
        print("   2. Wait for Supertrend to turn bullish again")
        print(f"   3. Set strict SL at ₹{STOP_LOSS:,.2f}")
    elif current_price >= ENTRY_PRICE:
        print("\n   ✅ HOLD - You're in profit or breakeven")
        print(f"   Trail your stop loss to ₹{current_price * 0.995:,.2f}")
    else:
        print("\n   ⏳ WAIT - Still within acceptable loss range")
        print(f"   Exit if price falls below ₹{STOP_LOSS:,.2f}")
    
    print("\n" + "=" * 70)

except Exception as e:
    print(f"\n❌ Error analyzing: {e}")
    print("Make sure market data is available.")
