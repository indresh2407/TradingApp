"""
EMA Crossover Strategy (Swing Trading)
Buy when fast EMA crosses above slow EMA
Sell when fast EMA crosses below slow EMA

TIME-AWARE: Targets are adjusted based on time remaining until 3:15 PM
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
from loguru import logger

from ..base_strategy import BaseStrategy, Signal, SignalType, get_intraday_time_multiplier


class EMACrossoverStrategy(BaseStrategy):
    """
    Swing Trading EMA Crossover Strategy
    
    Entry Conditions (Long):
    - EMA 9 crosses above EMA 21 (golden cross)
    - Price above EMA 21
    - Volume confirmation (optional)
    
    Exit Conditions:
    - EMA 9 crosses below EMA 21 (death cross)
    - Stop-loss hit
    - Target hit
    - Maximum holding period reached
    """
    
    def __init__(
        self,
        market_data,
        risk_manager,
        symbols: List[str],
        exchange: str = "NSE",
        fast_ema: int = 9,
        slow_ema: int = 21,
        require_volume_confirmation: bool = True
    ):
        super().__init__(
            market_data=market_data,
            risk_manager=risk_manager,
            symbols=symbols,
            exchange=exchange,
            timeframe="1D",  # Daily timeframe for swing trading
            start_time="09:30",
            end_time="15:15"
        )
        
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.require_volume_confirmation = require_volume_confirmation
    
    @property
    def name(self) -> str:
        return f"EMA Crossover ({self.fast_ema}/{self.slow_ema})"
    
    def _detect_crossover(self, data: pd.DataFrame) -> tuple:
        """Detect EMA crossover"""
        if len(data) < 2:
            return False, False
        
        fast_col = f"ema_{self.fast_ema}"
        slow_col = f"ema_{self.slow_ema}"
        
        if fast_col not in data.columns or slow_col not in data.columns:
            return False, False
        
        current_fast = data[fast_col].iloc[-1]
        current_slow = data[slow_col].iloc[-1]
        prev_fast = data[fast_col].iloc[-2]
        prev_slow = data[slow_col].iloc[-2]
        
        # Bullish crossover: fast crosses above slow
        bullish_cross = prev_fast <= prev_slow and current_fast > current_slow
        
        # Bearish crossover: fast crosses below slow
        bearish_cross = prev_fast >= prev_slow and current_fast < current_slow
        
        return bullish_cross, bearish_cross
    
    def _check_volume(self, data: pd.DataFrame) -> bool:
        """Check if volume confirms the signal"""
        if not self.require_volume_confirmation:
            return True
        
        if "volume_ratio" not in data.columns:
            return True  # Skip volume check if not available
        
        volume_ratio = data["volume_ratio"].iloc[-1]
        return volume_ratio > 1.0  # Volume above average
    
    def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[Signal]:
        """Analyze for entry signals"""
        if data.empty:
            return None
        
        bullish_cross, _ = self._detect_crossover(data)
        
        if not bullish_cross:
            return None
        
        # Volume confirmation
        if not self._check_volume(data):
            logger.debug(f"[{self.name}] {symbol}: Crossover without volume confirmation")
            return None
        
        current_price = data["close"].iloc[-1]
        
        # Calculate levels
        stoploss = self.calculate_stoploss(current_price, data)
        target = self.calculate_target(current_price, stoploss)
        quantity = self.calculate_quantity(symbol, current_price, stoploss)
        
        strength = 0.8  # Base strength for crossover
        
        # Increase strength if RSI is favorable
        if "rsi" in data.columns:
            rsi = data["rsi"].iloc[-1]
            if 40 < rsi < 60:
                strength = 0.9  # Strong if RSI is neutral
        
        logger.info(
            f"[{self.name}] BUY signal for {symbol}: "
            f"EMA crossover at ₹{current_price:.2f}"
        )
        
        return Signal(
            signal_type=SignalType.BUY,
            symbol=symbol,
            strength=strength,
            price=current_price,
            stoploss=stoploss,
            target=target,
            quantity=quantity,
            reason=f"EMA {self.fast_ema}/{self.slow_ema} bullish crossover",
            timestamp=datetime.now(),
            metadata={
                "crossover_type": "bullish",
                "strategy": self.name,
                "product": "CNC"  # Delivery for swing trading
            }
        )
    
    def should_exit(self, symbol: str, position: Dict[str, Any], data: pd.DataFrame) -> Optional[Signal]:
        """Check for exit conditions"""
        if data.empty:
            return None
        
        current_price = data["close"].iloc[-1]
        entry_price = position.get("entry_price", 0)
        stoploss_price = position.get("stoploss_price", 0)
        target_price = position.get("target_price", 0)
        quantity = position.get("quantity", 0)
        entry_time = position.get("entry_time")
        
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
        
        # Check bearish crossover
        _, bearish_cross = self._detect_crossover(data)
        if bearish_cross:
            logger.info(f"[{self.name}] Bearish crossover exit for {symbol}")
            return Signal(
                signal_type=SignalType.SELL,
                symbol=symbol,
                strength=0.8,
                price=current_price,
                stoploss=0,
                target=0,
                quantity=quantity,
                reason=f"EMA {self.fast_ema}/{self.slow_ema} bearish crossover",
                timestamp=datetime.now(),
                metadata={"exit_type": "crossover"}
            )
        
        # Check maximum holding period (10 days default)
        if entry_time:
            holding_days = (datetime.now() - entry_time).days
            max_days = self.risk_manager.config.__dict__.get("max_holding_days", 10)
            if holding_days >= max_days:
                logger.info(f"[{self.name}] Max holding period exit for {symbol}")
                return Signal(
                    signal_type=SignalType.SELL,
                    symbol=symbol,
                    strength=0.5,
                    price=current_price,
                    stoploss=0,
                    target=0,
                    quantity=quantity,
                    reason=f"Maximum holding period ({max_days} days) reached",
                    timestamp=datetime.now(),
                    metadata={"exit_type": "time_exit"}
                )
        
        return None
    
    def calculate_stoploss(self, price: float, data: pd.DataFrame) -> float:
        """Calculate stop-loss below slow EMA"""
        slow_col = f"ema_{self.slow_ema}"
        
        if slow_col in data.columns and not data[slow_col].isna().all():
            slow_ema = data[slow_col].iloc[-1]
            # Stop-loss 1% below slow EMA
            return slow_ema * 0.99
        
        # Default to 3% below entry for swing trades
        return price * 0.97
    
    def calculate_target(self, price: float, stoploss: float) -> float:
        """
        Calculate target with 2:1 risk-reward ratio
        
        TIME-AWARE: Target is reduced late in day to ensure achievability
        """
        risk = price - stoploss
        base_target = price + (risk * 2)  # 2:1 reward-to-risk
        
        # Apply time multiplier
        time_multiplier = get_intraday_time_multiplier()
        adjusted_target = price + (base_target - price) * time_multiplier
        
        return adjusted_target
