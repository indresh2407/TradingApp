"""
Kotak Neo API Client Wrapper
Handles authentication, session management, and API calls
"""

import os
import time
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

try:
    from neo_api_client import NeoAPI
except ImportError:
    NeoAPI = None
    logger.warning("neo_api_client not installed. Install with: pip install git+https://github.com/Kotak-Neo/kotak-neo-api.git#egg=neo_api_client")


class KotakClient:
    """Wrapper for Kotak Neo API with session management and error handling"""
    
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        mobile_number: str,
        password: str,
        mpin: str,
        environment: str = "uat",
        on_message: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.mobile_number = mobile_number
        self.password = password
        self.mpin = mpin
        self.environment = environment
        
        self._client: Optional[NeoAPI] = None
        self._is_authenticated = False
        self._session_expiry: Optional[datetime] = None
        self._last_activity: Optional[datetime] = None
        
        self._on_message = on_message or self._default_on_message
        self._on_error = on_error or self._default_on_error
        
    def _default_on_message(self, message: Dict[str, Any]) -> None:
        logger.info(f"Message received: {message}")
        
    def _default_on_error(self, error: Any) -> None:
        logger.error(f"Error received: {error}")
        
    def _default_on_close(self, message: Any) -> None:
        logger.info(f"Connection closed: {message}")
        
    def _default_on_open(self, message: Any) -> None:
        logger.info(f"Connection opened: {message}")
    
    @property
    def is_connected(self) -> bool:
        return self._is_authenticated and self._client is not None
    
    def connect(self, totp: str) -> bool:
        """
        Establish connection to Kotak Neo API
        
        Args:
            totp: Time-based OTP from authenticator app
            
        Returns:
            True if connection successful, False otherwise
        """
        if NeoAPI is None:
            logger.error("neo_api_client not installed")
            return False
            
        try:
            logger.info(f"Connecting to Kotak Neo API ({self.environment})...")
            
            self._client = NeoAPI(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                environment=self.environment,
                access_token=None,
                neo_fin_key=None
            )
            
            # Set callbacks
            self._client.on_message = self._on_message
            self._client.on_error = self._on_error
            self._client.on_close = self._default_on_close
            self._client.on_open = self._default_on_open
            
            # Login with mobile and password
            login_response = self._client.login(
                mobilenumber=self.mobile_number,
                password=self.password
            )
            logger.debug(f"Login response: {login_response}")
            
            # Complete 2FA with TOTP
            session_response = self._client.session_2fa(OTP=totp)
            logger.debug(f"2FA response: {session_response}")
            
            self._is_authenticated = True
            self._session_expiry = datetime.now() + timedelta(hours=8)
            self._last_activity = datetime.now()
            
            logger.info("Successfully connected to Kotak Neo API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self._is_authenticated = False
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the API"""
        if self._client:
            try:
                self._client.logout()
            except Exception as e:
                logger.warning(f"Error during logout: {e}")
            finally:
                self._client = None
                self._is_authenticated = False
                logger.info("Disconnected from Kotak Neo API")
    
    def _ensure_connected(self) -> None:
        """Ensure client is connected before making API calls"""
        if not self.is_connected:
            raise ConnectionError("Not connected to Kotak Neo API. Call connect() first.")
        self._last_activity = datetime.now()
    
    def place_order(
        self,
        symbol: str,
        exchange: str,
        transaction_type: str,  # "B" for Buy, "S" for Sell
        quantity: int,
        price: float = 0,
        order_type: str = "MKT",  # MKT, L, SL, SL-M
        product: str = "MIS",  # MIS, CNC, NRML
        trigger_price: float = 0,
        disclosed_quantity: int = 0,
        validity: str = "DAY",
        amo: bool = False,
    ) -> Dict[str, Any]:
        """
        Place an order
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE")
            exchange: Exchange segment (NSE, BSE, NFO)
            transaction_type: "B" for Buy, "S" for Sell
            quantity: Number of shares/lots
            price: Limit price (0 for market orders)
            order_type: MKT, L (Limit), SL, SL-M
            product: MIS (Intraday), CNC (Delivery), NRML (F&O)
            trigger_price: Trigger price for SL orders
            disclosed_quantity: Disclosed quantity
            validity: DAY, IOC
            amo: After Market Order flag
            
        Returns:
            Order response dictionary
        """
        self._ensure_connected()
        
        try:
            response = self._client.place_order(
                exchange_segment=exchange,
                product=product,
                price=str(price),
                order_type=order_type,
                quantity=str(quantity),
                validity=validity,
                trading_symbol=symbol,
                transaction_type=transaction_type,
                amo=str(amo).upper(),
                disclosed_quantity=str(disclosed_quantity),
                market_protection=str(0),
                pf="N",
                trigger_price=str(trigger_price),
                tag=None
            )
            
            logger.info(f"Order placed: {transaction_type} {quantity} {symbol} @ {price if price > 0 else 'MKT'}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise
    
    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        order_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Modify an existing order"""
        self._ensure_connected()
        
        try:
            response = self._client.modify_order(
                order_id=order_id,
                quantity=str(quantity) if quantity else None,
                price=str(price) if price else None,
                trigger_price=str(trigger_price) if trigger_price else None,
                order_type=order_type
            )
            
            logger.info(f"Order modified: {order_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to modify order {order_id}: {e}")
            raise
    
    def cancel_order(self, order_id: str, amo: bool = False) -> Dict[str, Any]:
        """Cancel an existing order"""
        self._ensure_connected()
        
        try:
            response = self._client.cancel_order(
                order_id=order_id,
                amo=str(amo).upper()
            )
            
            logger.info(f"Order cancelled: {order_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise
    
    def get_order_book(self) -> Dict[str, Any]:
        """Get list of all orders for the day"""
        self._ensure_connected()
        return self._client.order_report()
    
    def get_trade_book(self) -> Dict[str, Any]:
        """Get list of all executed trades"""
        self._ensure_connected()
        return self._client.trade_report()
    
    def get_positions(self) -> Dict[str, Any]:
        """Get current positions"""
        self._ensure_connected()
        return self._client.positions()
    
    def get_holdings(self) -> Dict[str, Any]:
        """Get portfolio holdings"""
        self._ensure_connected()
        return self._client.holdings()
    
    def get_margins(self) -> Dict[str, Any]:
        """Get available margins"""
        self._ensure_connected()
        return self._client.limits()
    
    def get_quote(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get live quote for a symbol"""
        self._ensure_connected()
        
        instrument_tokens = [{"instrument_token": symbol, "exchange_segment": exchange}]
        return self._client.quotes(instrument_tokens=instrument_tokens)
    
    def subscribe_feeds(
        self,
        symbols: list,
        exchange: str,
        on_tick: Optional[Callable] = None
    ) -> None:
        """Subscribe to live market feeds"""
        self._ensure_connected()
        
        instrument_tokens = [
            {"instrument_token": sym, "exchange_segment": exchange}
            for sym in symbols
        ]
        
        if on_tick:
            self._client.on_message = on_tick
            
        self._client.subscribe(instrument_tokens=instrument_tokens)
        logger.info(f"Subscribed to feeds: {symbols}")
    
    def unsubscribe_feeds(self, symbols: list, exchange: str) -> None:
        """Unsubscribe from market feeds"""
        self._ensure_connected()
        
        instrument_tokens = [
            {"instrument_token": sym, "exchange_segment": exchange}
            for sym in symbols
        ]
        
        self._client.un_subscribe(instrument_tokens=instrument_tokens)
        logger.info(f"Unsubscribed from feeds: {symbols}")
