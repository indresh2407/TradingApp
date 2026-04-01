"""
Risk Manager
Enforces position sizing, stop-losses, and daily loss limits
Critical for protecting capital
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class RiskConfig:
    """Risk management configuration"""
    capital: float = 100000
    max_position_pct: float = 10  # Max % of capital per position
    max_daily_loss_pct: float = 2  # Max daily loss %
    max_open_positions: int = 3
    mandatory_stoploss: bool = True
    default_stoploss_pct: float = 1.5
    default_target_pct: float = 3.0


@dataclass
class DailyStats:
    """Track daily trading statistics"""
    date: date = field(default_factory=date.today)
    realized_pnl: float = 0
    unrealized_pnl: float = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0
        return (self.winning_trades / self.total_trades) * 100


class RiskManager:
    """
    Manages trading risk and enforces limits
    
    Key responsibilities:
    - Position sizing based on capital and risk
    - Daily loss limit enforcement
    - Stop-loss validation
    - Maximum position limits
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        self.daily_stats = DailyStats()
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self._trading_enabled = True
        self._kill_switch_active = False
        
    @property
    def available_capital(self) -> float:
        """Calculate available capital after accounting for open positions"""
        used_capital = sum(
            pos.get("value", 0) for pos in self.open_positions.values()
        )
        return self.config.capital - used_capital
    
    @property
    def max_daily_loss(self) -> float:
        """Maximum allowed daily loss in INR"""
        return self.config.capital * (self.config.max_daily_loss_pct / 100)
    
    @property
    def max_position_value(self) -> float:
        """Maximum value allowed per position"""
        return self.config.capital * (self.config.max_position_pct / 100)
    
    @property
    def is_trading_enabled(self) -> bool:
        """Check if trading is currently allowed"""
        if self._kill_switch_active:
            return False
            
        if abs(self.daily_stats.total_pnl) >= self.max_daily_loss:
            if self.daily_stats.total_pnl < 0:
                logger.warning("Daily loss limit reached - trading disabled")
                return False
                
        return self._trading_enabled
    
    def activate_kill_switch(self, reason: str = "Manual activation") -> None:
        """Emergency stop all trading"""
        self._kill_switch_active = True
        logger.critical(f"KILL SWITCH ACTIVATED: {reason}")
    
    def deactivate_kill_switch(self) -> None:
        """Re-enable trading after kill switch"""
        self._kill_switch_active = False
        logger.info("Kill switch deactivated - trading re-enabled")
    
    def reset_daily_stats(self) -> None:
        """Reset daily statistics (call at start of each trading day)"""
        self.daily_stats = DailyStats()
        logger.info("Daily statistics reset")
    
    def calculate_position_size(
        self,
        symbol: str,
        price: float,
        stoploss_pct: Optional[float] = None,
        risk_per_trade_pct: float = 1.0
    ) -> Tuple[int, float]:
        """
        Calculate optimal position size based on risk parameters
        
        Args:
            symbol: Trading symbol
            price: Entry price
            stoploss_pct: Stop-loss percentage (default from config)
            risk_per_trade_pct: Percentage of capital to risk per trade
            
        Returns:
            Tuple of (quantity, position_value)
        """
        sl_pct = stoploss_pct or self.config.default_stoploss_pct
        
        # Risk amount per trade
        risk_amount = self.config.capital * (risk_per_trade_pct / 100)
        
        # Risk per share (based on stop-loss)
        risk_per_share = price * (sl_pct / 100)
        
        # Calculate quantity based on risk
        quantity_by_risk = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        # Also check max position value limit
        max_quantity_by_value = int(self.max_position_value / price) if price > 0 else 0
        
        # Also check available capital
        max_quantity_by_capital = int(self.available_capital / price) if price > 0 else 0
        
        # Take the minimum of all constraints
        final_quantity = min(quantity_by_risk, max_quantity_by_value, max_quantity_by_capital)
        final_quantity = max(1, final_quantity)  # At least 1 share
        
        position_value = final_quantity * price
        
        logger.debug(
            f"Position size for {symbol}: {final_quantity} shares @ ₹{price:.2f} "
            f"= ₹{position_value:.2f} (SL: {sl_pct}%)"
        )
        
        return final_quantity, position_value
    
    def validate_order(
        self,
        symbol: str,
        quantity: int,
        price: float,
        transaction_type: str,
        stoploss_price: Optional[float] = None,
        product: str = "MIS"
    ) -> Tuple[bool, str]:
        """
        Validate if an order can be placed based on risk rules
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            price: Order price
            transaction_type: "B" for Buy, "S" for Sell
            stoploss_price: Stop-loss price (required if mandatory_stoploss is True)
            product: Order product type
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check kill switch
        if self._kill_switch_active:
            return False, "Kill switch is active - all trading halted"
        
        # Check daily loss limit
        if not self.is_trading_enabled:
            return False, f"Daily loss limit of ₹{self.max_daily_loss:.2f} reached"
        
        # Check open positions limit (for new positions)
        is_new_position = symbol not in self.open_positions
        if is_new_position and transaction_type == "B":
            if len(self.open_positions) >= self.config.max_open_positions:
                return False, f"Maximum {self.config.max_open_positions} open positions reached"
        
        # Calculate position value
        position_value = quantity * price
        
        # Check position value limit
        if position_value > self.max_position_value:
            return False, (
                f"Position value ₹{position_value:.2f} exceeds max "
                f"₹{self.max_position_value:.2f}"
            )
        
        # Check available capital
        if transaction_type == "B" and position_value > self.available_capital:
            return False, (
                f"Insufficient capital. Required: ₹{position_value:.2f}, "
                f"Available: ₹{self.available_capital:.2f}"
            )
        
        # Check mandatory stop-loss
        if self.config.mandatory_stoploss and transaction_type == "B":
            if stoploss_price is None or stoploss_price <= 0:
                return False, "Stop-loss is mandatory for all orders"
            
            # Validate stop-loss is reasonable (not too tight or too wide)
            sl_pct = abs((price - stoploss_price) / price) * 100
            if sl_pct < 0.5:
                return False, f"Stop-loss too tight ({sl_pct:.1f}%). Minimum 0.5% recommended"
            if sl_pct > 10:
                return False, f"Stop-loss too wide ({sl_pct:.1f}%). Maximum 10% allowed"
        
        return True, "Order validated"
    
    def register_position(
        self,
        symbol: str,
        quantity: int,
        entry_price: float,
        stoploss_price: float,
        target_price: Optional[float] = None,
        product: str = "MIS"
    ) -> None:
        """Register a new open position"""
        self.open_positions[symbol] = {
            "symbol": symbol,
            "quantity": quantity,
            "entry_price": entry_price,
            "current_price": entry_price,
            "stoploss_price": stoploss_price,
            "target_price": target_price,
            "value": quantity * entry_price,
            "product": product,
            "entry_time": datetime.now(),
            "unrealized_pnl": 0
        }
        logger.info(f"Position registered: {quantity} {symbol} @ ₹{entry_price:.2f}")
    
    def update_position_price(self, symbol: str, current_price: float) -> None:
        """Update position with current price and calculate unrealized P&L"""
        if symbol not in self.open_positions:
            return
            
        pos = self.open_positions[symbol]
        pos["current_price"] = current_price
        pos["unrealized_pnl"] = (current_price - pos["entry_price"]) * pos["quantity"]
        
        # Update daily unrealized P&L
        self.daily_stats.unrealized_pnl = sum(
            p["unrealized_pnl"] for p in self.open_positions.values()
        )
    
    def close_position(
        self,
        symbol: str,
        exit_price: float,
        quantity: Optional[int] = None
    ) -> float:
        """
        Close a position and calculate realized P&L
        
        Returns:
            Realized P&L for the closed position
        """
        if symbol not in self.open_positions:
            logger.warning(f"No open position found for {symbol}")
            return 0
        
        pos = self.open_positions[symbol]
        close_qty = quantity or pos["quantity"]
        
        # Calculate realized P&L
        realized_pnl = (exit_price - pos["entry_price"]) * close_qty
        
        # Update daily stats
        self.daily_stats.realized_pnl += realized_pnl
        self.daily_stats.total_trades += 1
        if realized_pnl >= 0:
            self.daily_stats.winning_trades += 1
        else:
            self.daily_stats.losing_trades += 1
        
        # Remove or reduce position
        if close_qty >= pos["quantity"]:
            del self.open_positions[symbol]
            logger.info(
                f"Position closed: {symbol} @ ₹{exit_price:.2f}, "
                f"P&L: ₹{realized_pnl:.2f}"
            )
        else:
            pos["quantity"] -= close_qty
            pos["value"] = pos["quantity"] * pos["entry_price"]
            logger.info(
                f"Partial close: {close_qty} {symbol} @ ₹{exit_price:.2f}, "
                f"P&L: ₹{realized_pnl:.2f}"
            )
        
        # Update unrealized P&L
        self.daily_stats.unrealized_pnl = sum(
            p["unrealized_pnl"] for p in self.open_positions.values()
        )
        
        return realized_pnl
    
    def check_stoploss_hit(self, symbol: str, current_price: float) -> bool:
        """Check if stop-loss is hit for a position"""
        if symbol not in self.open_positions:
            return False
            
        pos = self.open_positions[symbol]
        sl_price = pos.get("stoploss_price", 0)
        
        if sl_price > 0 and current_price <= sl_price:
            logger.warning(f"STOP-LOSS HIT: {symbol} @ ₹{current_price:.2f}")
            return True
        return False
    
    def check_target_hit(self, symbol: str, current_price: float) -> bool:
        """Check if target is hit for a position"""
        if symbol not in self.open_positions:
            return False
            
        pos = self.open_positions[symbol]
        target_price = pos.get("target_price", 0)
        
        if target_price > 0 and current_price >= target_price:
            logger.info(f"TARGET HIT: {symbol} @ ₹{current_price:.2f}")
            return True
        return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Get risk management summary"""
        return {
            "capital": self.config.capital,
            "available_capital": self.available_capital,
            "open_positions": len(self.open_positions),
            "max_positions": self.config.max_open_positions,
            "daily_pnl": self.daily_stats.total_pnl,
            "max_daily_loss": self.max_daily_loss,
            "daily_trades": self.daily_stats.total_trades,
            "win_rate": self.daily_stats.win_rate,
            "trading_enabled": self.is_trading_enabled,
            "kill_switch": self._kill_switch_active
        }
