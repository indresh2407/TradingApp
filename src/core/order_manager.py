"""
Order Manager
Handles order placement, modification, cancellation, and tracking
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
from .trade_logger import log_trade as log_trade_to_file, update_position


class OrderStatus(Enum):
    PENDING = "pending"
    PLACED = "placed"
    OPEN = "open"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


class OrderType(Enum):
    MARKET = "MKT"
    LIMIT = "L"
    STOPLOSS = "SL"
    STOPLOSS_MARKET = "SL-M"


class ProductType(Enum):
    INTRADAY = "MIS"
    DELIVERY = "CNC"
    NORMAL = "NRML"


@dataclass
class Order:
    """Represents a trading order"""
    symbol: str
    exchange: str
    transaction_type: str  # B or S
    quantity: int
    price: float = 0
    order_type: str = "MKT"
    product: str = "MIS"
    trigger_price: float = 0
    stoploss_price: float = 0
    target_price: float = 0
    
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_price: float = 0
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    error_message: str = ""


class OrderManager:
    """
    Manages order lifecycle with safety features
    
    Features:
    - Duplicate order prevention
    - Order tracking and history
    - Retry logic for failed orders
    - Paper trading mode
    """
    
    def __init__(
        self,
        kotak_client,
        risk_manager,
        paper_mode: bool = True,
        retry_attempts: int = 3,
        retry_delay: float = 2.0,
        duplicate_cooldown: int = 60
    ):
        self.client = kotak_client
        self.risk_manager = risk_manager
        self.paper_mode = paper_mode
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.duplicate_cooldown = duplicate_cooldown
        
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        self._recent_orders: Dict[str, datetime] = {}
        self._paper_order_counter = 0
        
    def _generate_paper_order_id(self) -> str:
        """Generate unique order ID for paper trading"""
        self._paper_order_counter += 1
        return f"PAPER-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._paper_order_counter}"
    
    def _is_duplicate_order(self, symbol: str, transaction_type: str) -> bool:
        """Check if this is a duplicate order within cooldown period"""
        key = f"{symbol}:{transaction_type}"
        
        if key in self._recent_orders:
            last_order_time = self._recent_orders[key]
            elapsed = (datetime.now() - last_order_time).seconds
            
            if elapsed < self.duplicate_cooldown:
                logger.warning(
                    f"Duplicate order blocked: {symbol} {transaction_type} "
                    f"(cooldown: {self.duplicate_cooldown - elapsed}s remaining)"
                )
                return True
        
        return False
    
    def _record_order_time(self, symbol: str, transaction_type: str) -> None:
        """Record order time for duplicate prevention"""
        key = f"{symbol}:{transaction_type}"
        self._recent_orders[key] = datetime.now()
    
    def place_order(
        self,
        symbol: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        price: float = 0,
        order_type: str = "MKT",
        product: str = "MIS",
        trigger_price: float = 0,
        stoploss_price: float = 0,
        target_price: float = 0,
        skip_duplicate_check: bool = False
    ) -> Optional[Order]:
        """
        Place a new order with safety checks
        
        Args:
            symbol: Trading symbol
            exchange: Exchange segment (NSE, BSE, NFO)
            transaction_type: "B" for Buy, "S" for Sell
            quantity: Order quantity
            price: Limit price (0 for market orders)
            order_type: MKT, L, SL, SL-M
            product: MIS, CNC, NRML
            trigger_price: For stop-loss orders
            stoploss_price: Stop-loss price for risk management
            target_price: Target price for the position
            skip_duplicate_check: Skip duplicate order check
            
        Returns:
            Order object if successful, None otherwise
        """
        # Check duplicate
        if not skip_duplicate_check and self._is_duplicate_order(symbol, transaction_type):
            return None
        
        # Create order object
        order = Order(
            symbol=symbol,
            exchange=exchange,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            order_type=order_type,
            product=product,
            trigger_price=trigger_price,
            stoploss_price=stoploss_price,
            target_price=target_price
        )
        
        # Validate with risk manager
        effective_price = price if price > 0 else self._get_market_price(symbol, exchange)
        is_valid, reason = self.risk_manager.validate_order(
            symbol=symbol,
            quantity=quantity,
            price=effective_price,
            transaction_type=transaction_type,
            stoploss_price=stoploss_price,
            product=product
        )
        
        if not is_valid:
            order.status = OrderStatus.REJECTED
            order.error_message = reason
            logger.warning(f"Order rejected: {reason}")
            self.order_history.append(order)
            return order
        
        # Place order (paper or live)
        if self.paper_mode:
            order = self._place_paper_order(order, effective_price)
        else:
            order = self._place_live_order(order)
        
        # Track order
        if order.order_id:
            self.orders[order.order_id] = order
            self._record_order_time(symbol, transaction_type)
        
        self.order_history.append(order)
        
        # Register position if order successful
        if order.status == OrderStatus.COMPLETE and transaction_type == "B":
            self.risk_manager.register_position(
                symbol=symbol,
                quantity=quantity,
                entry_price=order.average_price or effective_price,
                stoploss_price=stoploss_price,
                target_price=target_price,
                product=product
            )
        
        return order
    
    def _get_market_price(self, symbol: str, exchange: str) -> float:
        """Get current market price for a symbol"""
        try:
            if self.paper_mode:
                return 100.0  # Placeholder for paper trading
            
            quote = self.client.get_quote(symbol, exchange)
            if quote and "data" in quote:
                return float(quote["data"].get("ltp", 0))
        except Exception as e:
            logger.error(f"Failed to get market price: {e}")
        return 0
    
    def _place_paper_order(self, order: Order, price: float) -> Order:
        """Simulate order execution in paper trading mode"""
        order.order_id = self._generate_paper_order_id()
        order.status = OrderStatus.COMPLETE
        order.filled_quantity = order.quantity
        order.average_price = price if price > 0 else order.price
        order.updated_at = datetime.now()
        
        logger.info(
            f"[PAPER] Order executed: {order.transaction_type} {order.quantity} "
            f"{order.symbol} @ ₹{order.average_price:.2f}"
        )
        
        # Log trade to file for dashboard
        log_trade_to_file(
            symbol=order.symbol,
            action="BUY" if order.transaction_type == "B" else "SELL",
            quantity=order.quantity,
            price=order.average_price,
            order_type=order.order_type,
            product=order.product,
            mode="PAPER",
            stoploss=order.stoploss_price,
            target=order.target_price,
            order_id=order.order_id
        )
        
        return order
    
    def _place_live_order(self, order: Order) -> Order:
        """Place actual order through Kotak API"""
        for attempt in range(self.retry_attempts):
            try:
                response = self.client.place_order(
                    symbol=order.symbol,
                    exchange=order.exchange,
                    transaction_type=order.transaction_type,
                    quantity=order.quantity,
                    price=order.price,
                    order_type=order.order_type,
                    product=order.product,
                    trigger_price=order.trigger_price
                )
                
                if response and "nOrdNo" in response:
                    order.order_id = response["nOrdNo"]
                    order.status = OrderStatus.PLACED
                    order.updated_at = datetime.now()
                    
                    logger.info(
                        f"Order placed: {order.order_id} - "
                        f"{order.transaction_type} {order.quantity} {order.symbol}"
                    )
                    
                    # Log trade to file for dashboard
                    log_trade_to_file(
                        symbol=order.symbol,
                        action="BUY" if order.transaction_type == "B" else "SELL",
                        quantity=order.quantity,
                        price=order.price,
                        order_type=order.order_type,
                        product=order.product,
                        mode="LIVE",
                        stoploss=order.stoploss_price,
                        target=order.target_price,
                        order_id=order.order_id
                    )
                    
                    return order
                else:
                    order.error_message = str(response)
                    
            except Exception as e:
                order.error_message = str(e)
                logger.error(f"Order attempt {attempt + 1} failed: {e}")
                
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
        
        order.status = OrderStatus.FAILED
        return order
    
    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None
    ) -> Optional[Order]:
        """Modify an existing order"""
        if order_id not in self.orders:
            logger.warning(f"Order not found: {order_id}")
            return None
        
        order = self.orders[order_id]
        
        if self.paper_mode:
            if quantity:
                order.quantity = quantity
            if price:
                order.price = price
            if trigger_price:
                order.trigger_price = trigger_price
            order.updated_at = datetime.now()
            logger.info(f"[PAPER] Order modified: {order_id}")
        else:
            try:
                self.client.modify_order(
                    order_id=order_id,
                    quantity=quantity,
                    price=price,
                    trigger_price=trigger_price
                )
                order.updated_at = datetime.now()
                logger.info(f"Order modified: {order_id}")
            except Exception as e:
                logger.error(f"Failed to modify order: {e}")
                return None
        
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        if order_id not in self.orders:
            logger.warning(f"Order not found: {order_id}")
            return False
        
        order = self.orders[order_id]
        
        if self.paper_mode:
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now()
            logger.info(f"[PAPER] Order cancelled: {order_id}")
            return True
        else:
            try:
                self.client.cancel_order(order_id)
                order.status = OrderStatus.CANCELLED
                order.updated_at = datetime.now()
                logger.info(f"Order cancelled: {order_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to cancel order: {e}")
                return False
    
    def cancel_all_orders(self) -> int:
        """Cancel all open orders"""
        cancelled = 0
        for order_id, order in self.orders.items():
            if order.status in [OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.OPEN]:
                if self.cancel_order(order_id):
                    cancelled += 1
        
        logger.info(f"Cancelled {cancelled} orders")
        return cancelled
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_open_orders(self) -> List[Order]:
        """Get all open orders"""
        return [
            order for order in self.orders.values()
            if order.status in [OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.OPEN]
        ]
    
    def sync_orders(self) -> None:
        """Sync order status with broker"""
        if self.paper_mode:
            return
        
        try:
            order_book = self.client.get_order_book()
            if not order_book or "data" not in order_book:
                return
            
            for broker_order in order_book["data"]:
                order_id = broker_order.get("nOrdNo")
                if order_id in self.orders:
                    order = self.orders[order_id]
                    status = broker_order.get("ordSt", "").lower()
                    
                    if status == "complete":
                        order.status = OrderStatus.COMPLETE
                        order.filled_quantity = int(broker_order.get("fldQty", 0))
                        order.average_price = float(broker_order.get("avgPrc", 0))
                    elif status == "cancelled":
                        order.status = OrderStatus.CANCELLED
                    elif status == "rejected":
                        order.status = OrderStatus.REJECTED
                        order.error_message = broker_order.get("rejRsn", "")
                    
                    order.updated_at = datetime.now()
                    
        except Exception as e:
            logger.error(f"Failed to sync orders: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get order manager summary"""
        return {
            "paper_mode": self.paper_mode,
            "total_orders": len(self.orders),
            "open_orders": len(self.get_open_orders()),
            "order_history": len(self.order_history)
        }
