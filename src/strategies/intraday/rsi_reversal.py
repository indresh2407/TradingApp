"""
RSI Reversal Strategy (Intraday)
Buy when RSI is oversold and showing reversal
Sell when RSI is overbought and showing reversal
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
from loguru import logger

from ..base_strategy import BaseStrategy, Signal, SignalType


class RSIReversalStrategy(BaseStrategy):
    """
    Intraday RSI Reversal Strategy
    
    Entry Conditions (Long):
    - RSI < 30 (oversold)
    - RSI turning up (current > previous)
    - Price above 20-period low
    
    Exit Conditions:
    - RSI > 70 (overbought)
    - Stop-loss hit
    - Target hit
    - End of day square-off
    """
    
    def __init__(
        self,
        market_data,
        risk_manager,
        symbols: List[str],
        exchange: str = "NSE",
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
        min_signal_strength: float = 0.5
    ):
        super().__init__(
            market_data=market_data,
            risk_manager=risk_manager,
            symbols=symbols,
            exchange=exchange,
            timeframe="5min",
            start_time="09:30",
            end_time="14:30"  # Stop new entries before 2:30 PM
        )
        
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.min_signal_strength = min_signal_strength
    
    @property
    def name(self) -> str:
        return "RSI Reversal (Intraday)"
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[Signal]:
        """Analyze for entry signals"""
        if data.empty or "rsi" not in data.columns:
            return None
        
        if len(data) < 2:
            return None
        
        current_rsi = data["rsi"].iloc[-1]
        prev_rsi = data["rsi"].iloc[-2]
        current_price = data["close"].iloc[-1]
        
        # Check for oversold reversal
        if current_rsi < self.rsi_oversold and current_rsi > prev_rsi:
            strength = min((self.rsi_oversold - current_rsi) / 10, 1.0)
            
            if strength >= self.min_signal_strength:
                stoploss = self.calculate_stoploss(current_price, data)
                target = self.calculate_target(current_price, stoploss)
                quantity = self.calculate_quantity(symbol, current_price, stoploss)
                
                logger.info(
                    f"[{self.name}] BUY signal for {symbol}: "
                    f"RSI={current_rsi:.1f}, Price=₹{current_price:.2f}"
                )
                
                return Signal(
                    signal_type=SignalType.BUY,
                    symbol=symbol,
                    strength=strength,
                    price=current_price,
                    stoploss=stoploss,
                    target=target,
                    quantity=quantity,
                    reason=f"RSI oversold reversal ({current_rsi:.1f})",
                    timestamp=datetime.now(),
                    metadata={
                        "rsi": current_rsi,
                        "prev_rsi": prev_rsi,
                        "strategy": self.name
                    }
                )
        
        return None
    
    def should_exit(self, symbol: str, position: Dict[str, Any], data: pd.DataFrame) -> Optional[Signal]:
        """Check for exit conditions"""
        if data.empty or "rsi" not in data.columns:
            return None
        
        current_rsi = data["rsi"].iloc[-1]
        current_price = data["close"].iloc[-1]
        entry_price = position.get("entry_price", 0)
        stoploss_price = position.get("stoploss_price", 0)
        target_price = position.get("target_price", 0)
        quantity = position.get("quantity", 0)
        
        # Check stop-loss
        if stoploss_price > 0 and current_price <= stoploss_price:
            logger.warning(f"[{self.name}] STOP-LOSS triggered for {symbol}")
            return Signal(
                signal_type=SignalType.SELL,
                symbol=symbol,
                strength=1.0,
                price=current_price,
                stoploss=0,
                target=0,
                quantity=quantity,
                reason="Stop-loss triggered",
                timestamp=datetime.now(),
                metadata={"exit_type": "stoploss"}
            )
        
        # Check target
        if target_price > 0 and current_price >= target_price:
            logger.info(f"[{self.name}] TARGET hit for {symbol}")
            return Signal(
                signal_type=SignalType.SELL,
                symbol=symbol,
                strength=1.0,
                price=current_price,
                stoploss=0,
                target=0,
                quantity=quantity,
                reason="Target achieved",
                timestamp=datetime.now(),
                metadata={"exit_type": "target"}
            )
        
        # Check RSI overbought
        if current_rsi > self.rsi_overbought:
            logger.info(f"[{self.name}] RSI overbought exit for {symbol}")
            return Signal(
                signal_type=SignalType.SELL,
                symbol=symbol,
                strength=0.8,
                price=current_price,
                stoploss=0,
                target=0,
                quantity=quantity,
                reason=f"RSI overbought ({current_rsi:.1f})",
                timestamp=datetime.now(),
                metadata={"exit_type": "rsi_overbought", "rsi": current_rsi}
            )
        
        return None
    
    def calculate_stoploss(self, price: float, data: pd.DataFrame) -> float:
        """Calculate stop-loss using ATR if available"""
        if "atr" in data.columns and not data["atr"].isna().all():
            atr = data["atr"].iloc[-1]
            return price - (1.5 * atr)  # 1.5x ATR below entry
        
        # Default to percentage-based stop-loss
        return super().calculate_stoploss(price, data)
