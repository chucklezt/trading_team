"""Scanner Agent - Detects arbitrage opportunities across exchanges."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from agents.common.message_queue import MessageQueue
from agents.common.models import Opportunity, OpportunityStatus
from agents.common import setup_logging

# Setup logging
setup_logging(__name__)

logger = logging.getLogger(__name__)


class ExchangeConnector:
    """
    Base class for exchange connectors.
    """
    
    def __init__(self, name: str, api_key: str, api_secret: str):
        self.name = name
        self.api_key = api_key
        self.api_secret = api_secret
        self.websocket = None
        self.rest_api = None
    
    async def connect(self):
        """Establish connection to exchange."""
        raise NotImplementedError
    
    async def disconnect(self):
        """Close connection to exchange."""
        raise NotImplementedError
    
    async def get_ticker(self, symbol: str) -> Optional[dict]:
        """Get current ticker price."""
        raise NotImplementedError
    
    async def get_order_book(self, symbol: str, limit: int = 10) -> Optional[dict]:
        """Get order book for symbol."""
        raise NotImplementedError


class BinanceConnector(ExchangeConnector):
    """Binance exchange connector."""
    
    def __init__(self, api_key: str, api_secret: str):
        super().__init__("binance", api_key, api_secret)
        self.rest_api = "https://api.binance.com/api/v3"
        self.ws_url = "wss://stream.binance.com:9443/ws"
    
    async def connect(self):
        """Connect to Binance WebSocket."""
        # Implementation would use aiohttp or websockets
        logger.info(f"Connected to {self.name}")
    
    async def disconnect(self):
        """Disconnect from Binance."""
        logger.info(f"Disconnected from {self.name}")
    
    async def get_ticker(self, symbol: str) -> Optional[dict]:
        """Get Binance ticker."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.rest_api}/ticker/24hr/{symbol.upper()}") as response:
                if response.status == 200:
                    return await response.json()
        return None
    
    async def get_order_book(self, symbol: str, limit: int = 10) -> Optional[dict]:
        """Get Binance order book."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.rest_api}/depth?symbol={symbol.upper()}&limit={limit}") as response:
                if response.status == 200:
                    return await response.json()
        return None


class CoinbaseConnector(ExchangeConnector):
    """Coinbase exchange connector."""
    
    def __init__(self, api_key: str, api_secret: str, passphrase: str):
        super().__init__("coinbase", api_key, api_secret)
        self.rest_api = "https://api.exchange.coinbase.com"
        self.ws_url = "wss://ws-feed.exchange.coinbase.com"
        self.passphrase = passphrase
    
    async def connect(self):
        """Connect to Coinbase WebSocket."""
        logger.info(f"Connected to {self.name}")
    
    async def disconnect(self):
        """Disconnect from Coinbase."""
        logger.info(f"Disconnected from {self.name}")
    
    async def get_ticker(self, symbol: str) -> Optional[dict]:
        """Get Coinbase ticker."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.rest_api}/products/{symbol}/ticker") as response:
                if response.status == 200:
                    return await response.json()
        return None
    
    async def get_order_book(self, symbol: str, limit: int = 10) -> Optional[dict]:
        """Get Coinbase order book."""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.rest_api}/products/{symbol}/book?level=5") as response:
                if response.status == 200:
                    return await response.json()
        return None


class ScannerAgent:
    """
    Scanner Agent monitors multiple exchanges for arbitrage opportunities.
    
    Responsibilities:
    - Connect to multiple exchanges via WebSocket and REST APIs
    - Parse real-time price feeds
    - Detect price discrepancies
    - Calculate opportunity metrics
    - Queue opportunities for validation
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.message_queue = MessageQueue()
        self.exchange_connectors: Dict[str, ExchangeConnector] = {}
        self.subscribed_symbols: Dict[str, set] = {}
        self.running = False
        self.last_prices: Dict[str, dict] = {}
        
        # Initialize exchange connectors
        self._initialize_connectors()
    
    def _initialize_connectors(self):
        """Initialize exchange connectors from config."""
        for exchange_config in self.config.get('exchanges', []):
            name = exchange_config['name']
            
            if name == 'binance':
                connector = BinanceConnector(
                    api_key=exchange_config.get('api_key', ''),
                    api_secret=exchange_config.get('api_secret', '')
                )
            elif name == 'coinbase':
                connector = CoinbaseConnector(
                    api_key=exchange_config.get('api_key', ''),
                    api_secret=exchange_config.get('api_secret', ''),
                    passphrase=exchange_config.get('passphase', '')
                )
            else:
                logger.warning(f"Unknown exchange: {name}")
                continue
            
            self.exchange_connectors[name] = connector
            
            # Initialize subscribed symbols
            self.subscribed_symbols[name] = set(
                symbol.upper() for symbol in exchange_config.get('symbols', [])
            )
    
    async def start(self):
        """Start the scanner agent."""
        logger.info("Starting Scanner Agent")
        self.running = True
        
        # Connect to all exchanges
        for name, connector in self.exchange_connectors.items():
            try:
                await connector.connect()
                logger.info(f"Scanner connected to {name}")
            except Exception as e:
                logger.error(f"Failed to connect to {name}: {e}")
        
        # Start monitoring loop
        await self._monitor_loop()
    
    async def stop(self):
        """Stop the scanner agent."""
        logger.info("Stopping Scanner Agent")
        self.running = False
        
        # Disconnect from all exchanges
        for name, connector in self.exchange_connectors.items():
            try:
                await connector.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from {name}: {e}")
        
        logger.info("Scanner Agent stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Check all exchange pairs
                await self._check_opportunities()
                
                # Wait for next iteration
                await asyncio.sleep(1)  # 1 second interval
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def _check_opportunities(self):
        """Check for arbitrage opportunities across all exchanges."""
        exchanges = list(self.exchange_connectors.keys())
        
        for i in range(len(exchanges)):
            for j in range(i + 1, len(exchanges)):
                exchange1 = exchanges[i]
                exchange2 = exchanges[j]
                
                # Find common symbols
                symbols1 = self.subscribed_symbols.get(exchange1, set())
                symbols2 = self.subscribed_symbols.get(exchange2, set())
                common_symbols = symbols1 & symbols2
                
                for symbol in common_symbols:
                    try:
                        await self._check_pair(
                            exchange1, exchange2, symbol
                        )
                    except Exception as e:
                        logger.error(
                            f"Error checking {exchange1}/{exchange2}/{symbol}: {e}"
                        )
    
    async def _check_pair(self, exchange1: str, exchange2: str, symbol: str):
        """
        Check for arbitrage opportunity between two exchanges.
        
        Args:
            exchange1: First exchange name
            exchange2: Second exchange name
            symbol: Trading symbol
        """
        connector1 = self.exchange_connectors[exchange1]
        connector2 = self.exchange_connectors[exchange2]
        
        # Get prices from both exchanges
        price1 = await connector1.get_ticker(symbol)
        price2 = await connector2.get_ticker(symbol)
        
        if not price1 or not price2:
            return
        
        # Get bid/ask for better accuracy
        order_book1 = await connector1.get_order_book(symbol)
        order_book2 = await connector2.get_order_book(symbol)
        
        # Calculate best bid and ask
        buy_price = self._get_best_bid(order_book1, price1)
        sell_price = self._get_best_ask(order_book2, price2)
        
        if not buy_price or not sell_price:
            return
        
        # Check if there's an arbitrage opportunity
        spread = sell_price - buy_price
        spread_percentage = (spread / buy_price) * 100
        
        min_threshold = self.config.get('thresholds', {}).get(
            'min_spread_percentage', 0.1
        )
        
        if spread_percentage >= min_threshold:
            # Calculate potential profit
            quantity = self._calculate_max_quantity(buy_price, exchange1)
            gross_profit = spread * quantity
            
            # Estimate fees
            buy_fee = quantity * buy_price * 0.001  # 0.1% maker fee
            sell_fee = quantity * sell_price * 0.001
            withdrawal_fee = self._get_withdrawal_fee(
                self._get_base_asset(symbol), exchange1
            )
            total_fees = buy_fee + sell_fee + withdrawal_fee
            
            # Calculate net profit
            net_profit = gross_profit - total_fees
            
            # Calculate confidence score
            confidence = self._calculate_confidence(
                spread_percentage, quantity, order_book1, order_book2
            )
            
            # Create opportunity
            opportunity = Opportunity(
                asset=self._get_base_asset(symbol),
                buy_exchange=exchange1,
                buy_price=buy_price,
                sell_exchange=exchange2,
                sell_price=sell_price,
                quantity=quantity,
                gross_spread=spread,
                net_profit=net_profit,
                confidence=confidence
            )
            
            # Publish opportunity
            await self.message_queue.send_opportunity(opportunity.to_dict())
            
            logger.info(
                f"Opportunity detected: {symbol} "
                f"{exchange1}={buy_price} -> {exchange2}={sell_price}, "
                f"Net profit: ${net_profit:.2f}, Confidence: {confidence:.2f}"
            )
    
    def _get_best_bid(self, order_book: Optional[dict], ticker: Optional[dict]) -> Optional[float]:
        """Get best bid price."""
        if order_book:
            bids = order_book.get('bids', [])
            if bids:
                return float(bids[0][0])
        
        if ticker:
            # Use bid from ticker if order book unavailable
            return float(ticker.get('bid', 0))
        
        return None
    
    def _get_best_ask(self, order_book: Optional[dict], ticker: Optional[dict]) -> Optional[float]:
        """Get best ask price."""
        if order_book:
            asks = order_book.get('asks', [])
            if asks:
                return float(asks[0][0])
        
        if ticker:
            return float(ticker.get('ask', 0))
        
        return None
    
    def _calculate_max_quantity(self, price: float, exchange: str) -> float:
        """
        Calculate maximum quantity for arbitrage.
        
        Considers:
        - Account balance
        - Minimum order size
        - Maximum order size
        - Withdrawal limits
        """
        # Get account balance (would need to call exchange API)
        balance = self._get_exchange_balance(exchange)
        
        if balance <= 0:
            return 0.0
        
        min_size = self._get_min_order_size(exchange)
        max_size = self._get_max_order_size(exchange)
        min_withdrawal = self._get_min_withdrawal(exchange)
        
        # Calculate max quantity
        max_quantity = (balance / price) - min_withdrawal
        
        # Apply order size constraints
        max_quantity = max(min_size, min(max_quantity, max_size))
        
        return max_quantity
    
    def _get_exchange_balance(self, exchange: str) -> float:
        """Get exchange balance (placeholder)."""
        # Would call exchange API to get actual balance
        # For now, return a default value
        return 1.0  # 1.0 BTC/ETH equivalent
    
    def _get_min_order_size(self, exchange: str) -> float:
        """Get minimum order size for exchange."""
        min_sizes = {
            'binance': 0.0001,
            'coinbase': 0.0001
        }
        return min_sizes.get(exchange, 0.0001)
    
    def _get_max_order_size(self, exchange: str) -> float:
        """Get maximum order size for exchange."""
        max_sizes = {
            'binance': 1000.0,
            'coinbase': 1000.0
        }
        return max_sizes.get(exchange, 1000.0)
    
    def _get_min_withdrawal(self, exchange: str) -> float:
        """Get minimum withdrawal amount for exchange."""
        min_withdrawals = {
            'binance': 0.0005,
            'coinbase': 0.001
        }
        return min_withdrawals.get(exchange, 0.001)
    
    def _get_withdrawal_fee(self, asset: str, exchange: str) -> float:
        """Get withdrawal fee for asset on exchange."""
        fees = {
            ('BTC', 'binance'): 0.0002,
            ('ETH', 'binance'): 0.001,
            ('BTC', 'coinbase'): 0.0001,
            ('ETH', 'coinbase'): 0.001
        }
        return fees.get((asset, exchange), 0.0)
    
    def _get_base_asset(self, symbol: str) -> str:
        """Extract base asset from symbol."""
        # Symbol format: BASE/QUOTE or BASE-QUOTE
        return symbol.split('/')[0].split('-')[0]
    
    def _calculate_confidence(self, spread_percentage: float,
                              quantity: float,
                              order_book1: Optional[dict],
                              order_book2: Optional[dict]) -> float:
        """
        Calculate confidence score for opportunity.
        
        Higher confidence = more likely to be a real opportunity
        """
        score = 0.5  # Base score
        
        # Spread contribution (larger spread = higher confidence)
        score += min(spread_percentage / 10, 0.3)  # Max 0.3 from spread
        
        # Liquidity contribution
        liquidity1 = len(order_book1.get('bids', [])) if order_book1 else 0
        liquidity2 = len(order_book2.get('bids', [])) if order_book2 else 0
        avg_liquidity = (liquidity1 + liquidity2) / 2
        
        score += min(avg_liquidity / 20, 0.2)  # Max 0.2 from liquidity
        
        # Size contribution (larger trades = lower confidence)
        score -= min(quantity / 10, 0.2)  # Max 0.2 reduction
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
