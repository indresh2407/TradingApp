"""
Position Tracker
Monitors open positions and calculates P&L
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, time
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class Position:
    """Represents an open trading position"""
    symbol: str
    exchange: str
    quantity: int
    entry_price: float
    current_price: float
    stoploss_price: float
    target_price: float
    product: str
    entry_time: datetime
    
    @property
    def value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def invested_value(self) -> float:
        return self.quantity * self.entry_price
    
    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.entry_price) * self.quantity
    
    @property
    def unrealized_pnl_pct(self) -> float:
        if self.entry_price == 0:
            return 0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100
    
    @property
    def is_profit(self) -> bool:
        return self.unrealized_pnl >= 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "stoploss_price": self.stoploss_price,
            "target_price": self.target_price,
            "product": self.product,
            "entry_time": self.entry_time.isoformat(),
            "invested_value": self.invested_value,
            "current_value": self.value,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct
        }


class PositionTracker:
    """
    Tracks and monitors all open positions
    
    Features:
    - Real-time P&L calculation
    - Stop-loss and target monitoring
    - Intraday auto square-off
    - Position history
    """
    
    def __init__(
        self,
        kotak_client,
        risk_manager,
        order_manager,
        squareoff_time: str = "15:15"
    ):
        self.client = kotak_client
        self.risk_manager = risk_manager
        self.order_manager = order_manager
        self.squareoff_time = datetime.strptime(squareoff_time, "%H:%M").time()
        
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Dict[str, Any]] = []
        
    def add_position(
        self,
        symbol: str,
        exchange: str,
        quantity: int,
        entry_price: float,
        stoploss_price: float,
        target_price: float,
        product: str = "MIS"
    ) -> Position:
        """Add a new position to track"""
        position = Position(
            symbol=symbol,
            exchange=exchange,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            stoploss_price=stoploss_price,
            target_price=target_price,
            product=product,
            entry_time=datetime.now()
        )
        
        self.positions[symbol] = position
        logger.info(f"Position added: {quantity} {symbol} @ ₹{entry_price:.2f}")
        
        return position
    
    def update_price(self, symbol: str, current_price: float) -> None:
        """Update current price for a position"""
        if symbol in self.positions:
            self.positions[symbol].current_price = current_price
            self.risk_manager.update_position_price(symbol, current_price)
    
    def update_all_prices(self) -> None:
        """Update prices for all positions from market data"""
        for symbol, position in self.positions.items():
            try:
                if self.order_manager.paper_mode:
                    continue
                    
                quote = self.client.get_quote(symbol, position.exchange)
                if quote and "data" in quote:
                    ltp = float(quote["data"].get("ltp", 0))
                    if ltp > 0:
                        self.update_price(symbol, ltp)
            except Exception as e:
                logger.error(f"Failed to update price for {symbol}: {e}")
    
    def check_stoploss(self) -> List[str]:
        """Check all positions for stop-loss hits"""
        triggered = []
        
        for symbol, position in list(self.positions.items()):
            if position.current_price <= position.stoploss_price:
                logger.warning(
                    f"STOP-LOSS TRIGGERED: {symbol} @ ₹{position.current_price:.2f} "
                    f"(SL: ₹{position.stoploss_price:.2f})"
                )
                triggered.append(symbol)
        
        return triggered
    
    def check_targets(self) -> List[str]:
        """Check all positions for target hits"""
        triggered = []
        
        for symbol, position in list(self.positions.items()):
            if position.target_price > 0 and position.current_price >= position.target_price:
                logger.info(
                    f"TARGET HIT: {symbol} @ ₹{position.current_price:.2f} "
                    f"(Target: ₹{position.target_price:.2f})"
                )
                triggered.append(symbol)
        
        return triggered
    
    def close_position(
        self,
        symbol: str,
        exit_price: Optional[float] = None,
        reason: str = "manual"
    ) -> Optional[Dict[str, Any]]:
        """Close a position and record the trade"""
        if symbol not in self.positions:
            logger.warning(f"Position not found: {symbol}")
            return None
        
        position = self.positions[symbol]
        final_price = exit_price or position.current_price
        
        # Place sell order
        order = self.order_manager.place_order(
            symbol=symbol,
            exchange=position.exchange,
            transaction_type="S",
            quantity=position.quantity,
            price=0,  # Market order
            order_type="MKT",
            product=position.product,
            skip_duplicate_check=True
        )
        
        if order and order.status.value in ["complete", "placed"]:
            actual_price = order.average_price if order.average_price > 0 else final_price
            
            # Record closed position
            closed_record = {
                **position.to_dict(),
                "exit_price": actual_price,
                "exit_time": datetime.now().isoformat(),
                "realized_pnl": (actual_price - position.entry_price) * position.quantity,
                "reason": reason
            }
            self.closed_positions.append(closed_record)
            
            # Update risk manager
            self.risk_manager.close_position(symbol, actual_price)
            
            # Remove from active positions
            del self.positions[symbol]
            
            logger.info(
                f"Position closed: {symbol} @ ₹{actual_price:.2f}, "
                f"P&L: ₹{closed_record['realized_pnl']:.2f} ({reason})"
            )
            
            return closed_record
        else:
            logger.error(f"Failed to close position: {symbol}")
            return None
    
    def close_all_positions(self, reason: str = "manual") -> List[Dict[str, Any]]:
        """Close all open positions"""
        closed = []
        
        for symbol in list(self.positions.keys()):
            result = self.close_position(symbol, reason=reason)
            if result:
                closed.append(result)
        
        return closed
    
    def should_squareoff(self) -> bool:
        """Check if it's time for intraday square-off"""
        now = datetime.now().time()
        return now >= self.squareoff_time
    
    def squareoff_intraday(self) -> List[Dict[str, Any]]:
        """Square off all intraday positions"""
        intraday_positions = [
            symbol for symbol, pos in self.positions.items()
            if pos.product == "MIS"
        ]
        
        closed = []
        for symbol in intraday_positions:
            result = self.close_position(symbol, reason="intraday_squareoff")
            if result:
                closed.append(result)
        
        if closed:
            logger.info(f"Intraday square-off: Closed {len(closed)} positions")
        
        return closed
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get a specific position"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions as dictionaries"""
        return [pos.to_dict() for pos in self.positions.values()]
    
    def get_total_pnl(self) -> Dict[str, float]:
        """Get total unrealized P&L"""
        total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_invested = sum(pos.invested_value for pos in self.positions.values())
        
        return {
            "unrealized_pnl": total_pnl,
            "total_invested": total_invested,
            "pnl_pct": (total_pnl / total_invested * 100) if total_invested > 0 else 0
        }
    
    def sync_with_broker(self) -> None:
        """Sync positions with broker data"""
        if self.order_manager.paper_mode:
            return
        
        try:
            broker_positions = self.client.get_positions()
            if not broker_positions or "data" not in broker_positions:
                return
            
            for bp in broker_positions["data"]:
                symbol = bp.get("trdSym", "")
                if not symbol:
                    continue
                
                qty = int(bp.get("flBuyQty", 0)) - int(bp.get("flSellQty", 0))
                if qty == 0:
                    if symbol in self.positions:
                        del self.positions[symbol]
                    continue
                
                if symbol in self.positions:
                    self.positions[symbol].quantity = abs(qty)
                    ltp = float(bp.get("ltp", 0))
                    if ltp > 0:
                        self.positions[symbol].current_price = ltp
                        
        except Exception as e:
            logger.error(f"Failed to sync positions: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get position tracker summary"""
        pnl = self.get_total_pnl()
        return {
            "open_positions": len(self.positions),
            "closed_today": len(self.closed_positions),
            "unrealized_pnl": pnl["unrealized_pnl"],
            "total_invested": pnl["total_invested"],
            "pnl_pct": pnl["pnl_pct"]
        }
