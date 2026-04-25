"""Executor Agent - Places and monitors orders."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from agents.common.message_queue import MessageQueue
from agents.common.models import Order, OrderSide, OrderStatus
from agents.common import setup_logging

setup_logging(__name__)
logger = logging.getLogger(__name__)


class OrderManager:
    """Manages orders across exchanges."""
    
    def __init__(self):
        self.open_orders: Dict[str, Order] = {}
        self.filled_orders: Dict[str, Order] = {}
        self.cancelled_orders: Dict[str, Order] = {}
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.open_orders.get(order_id) or self.filled_orders.get(order_id) or self.cancelled_orders.get(order_id)
    
    def get_open_orders(self) -> List[Order]:
        """Get all open orders."""
        return list(self.open_orders.values())
    
    def get_filled_orders(self) -> List[Order]:
        """Get all filled orders."""
        return list(self.filled_orders.values())
    
    def add_order(self, order: Order):
        """Add order to tracking."""
        self.open_orders[order.order_id] = order
    
    def update_order(self, order: Order):
        """Update order status."""
        if order.order_id in self.open_orders:
            del self.open_orders[order.order_id]
        
        if order.status == OrderStatus.FILLED:
            self.filled_orders[order.order_id] = order
        elif order.status == OrderStatus.CANCELLED:
            self.cancelled_orders[order.order_id] = order
        else:
            self.open_orders[order.order_id] = order


class ExecutorAgent:
    """
    Executor Agent places and monitors orders.
    
    Responsibilities:
    - Place buy and sell orders
    - Monitor order status
    - Handle partial fills
    - Cancel failed orders
    - Execute settlement
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.message_queue = MessageQueue()
        self.order_manager = OrderManager()
        self.running = False
        
        # Execution settings
        self.timeout = config.get('timeout', {}).get('order_timeout', 60)
        self.retry_config = config.get('retry', {
            'max_attempts': 3,
            'initial_delay': 5,
            'exponential_backoff': True
        })
    
    async def start(self):
        """Start the executor agent."""
        logger.info("Starting Executor Agent")
        self.running = True
        
        # Subscribe to risk assessments
        await self.message_queue.subscribe(
            'trading:risk',
            self._process_risk_assessment
        )
        
        # Subscribe to execution results
        await self.message_queue.subscribe(
            'trading:reconciliation',
            self._process_execution_result
        )
    
    async def stop(self):
        """Stop the executor agent."""
        logger.info("Stopping Executor Agent")
        self.running = False
    
    async def _process_risk_assessment(self, message_data: str):
        """Process risk assessment and execute if approved."""
        try:
            message = self.message_queue._deserialize_message(message_data)
            
            if not message.get('assessment', {}).get('approved', False):
                logger.info("Risk assessment rejected, skipping execution")
                return
            
            opportunity_id = message.get('opportunity_id')
            
            # Extract opportunity data from original message
            original_data = self._get_original_message(opportunity_id)
            if not original_data:
                logger.warning(f"Could not find original opportunity for {opportunity_id}")
                return
            
            # Create and execute orders
            orders = await self._create_and_execute_orders(
                original_data,
                message.get('assessment', {})
            )
            
            # Track orders
            for order in orders:
                self.order_manager.add_order(order)
            
            logger.info(f"Executed orders for {opportunity_id}: {len(orders)} orders")
            
        except Exception as e:
            logger.error(f"Error processing risk assessment: {e}")
    
    async def _process_execution_result(self, message_data: str):
        """Process execution result."""
        try:
            message = self.message_queue._deserialize_message(message_data)
            
            order_id = message.get('order_id')
            result = message.get('result', {})
            
            # Update order status
            order = self.order_manager.get_order(order_id)
            if order:
                order.status = OrderStatus(result.get('status', 'filled'))
                order.filled_quantity = result.get('fill_quantity', 0)
                order.average_fill_price = result.get('fill_price', order.price)
                order.updated_at = datetime.utcnow()
                
                logger.info(f"Order {order_id} updated: {result.get('status')}")
                
        except Exception as e:
            logger.error(f"Error processing execution result: {e}")
    
    async def _create_and_execute_orders(self, message: dict, assessment: dict) -> List[Order]:
        """
        Create and execute orders for an opportunity.
        
        Args:
            message: Original opportunity message
            assessment: Risk assessment
            
        Returns:
            List of created orders
        """
        orders = []
        
        # Extract opportunity data
        data = message.get('data', {})
        opportunity_id = message.get('correlation_id')
        
        buy_exchange = data.get('buy_exchange')
        sell_exchange = data.get('sell_exchange')
        quantity = data.get('quantity')
        buy_price = data.get('buy_price')
        sell_price = data.get('sell_price')
        
        if not all([buy_exchange, sell_exchange, quantity, buy_price, sell_price]):
            logger.error("Invalid opportunity data")
            return orders
        
        # Create buy order
        buy_order = await self._create_order(
            exchange=buy_exchange,
            symbol=self._get_symbol(buy_exchange, data),
            side=OrderSide.BUY,
            quantity=quantity,
            price=buy_price,
            opportunity_id=opportunity_id
        )
        
        # Create sell order
        sell_order = await self._create_order(
            exchange=sell_exchange,
            symbol=self._get_symbol(sell_exchange, data),
            side=OrderSide.SELL,
            quantity=quantity,
            price=sell_price,
            opportunity_id=opportunity_id
        )
        
        orders.extend([buy_order, sell_order])
        
        # Execute orders with retry logic
        for order in orders:
            await self._execute_order_with_retry(order)
        
        return orders
    
    async def _create_order(self, exchange: str, symbol: str, side: OrderSide,
                            quantity: float, price: float, opportunity_id: str) -> Order:
        """Create an order."""
        order_id = f"{exchange}_{opportunity_id}_{side.value}_{datetime.utcnow().timestamp()}"
        
        order = Order(
            order_id=order_id,
            opportunity_id=opportunity_id,
            position_id="",  # Would be set after position creation
            exchange=exchange,
            symbol=symbol,
            side=side,
            order_type="limit",
            quantity=quantity,
            price=price,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        logger.info(f"Created order {order_id}: {side.value} {quantity} {symbol} @ {price}")
        
        return order
    
    def _get_symbol(self, exchange: str, data: dict) -> str:
        """Get trading symbol for exchange."""
        # Extract symbol from data
        # In production, would map exchange-specific symbols
        return data.get('asset', 'BTC') + '/' + data.get('quote', 'USDT')
    
    async def _execute_order_with_retry(self, order: Order):
        """
        Execute order with retry logic.
        
        Args:
            order: Order to execute
        """
        max_attempts = self.retry_config['max_attempts']
        delay = self.retry_config['initial_delay']
        exponential_backoff = self.retry_config['exponential_backoff']
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"Attempting to execute order {order.order_id} (attempt {attempt + 1}/{max_attempts})")
                
                # Simulate order execution
                result = await self._place_order(order)
                
                if result['status'] == 'success':
                    logger.info(f"Order {order.order_id} executed successfully")
                    return
                
                elif result['status'] == 'partial_fill':
                    # Update order with partial fill
                    order.filled_quantity = result.get('filled_quantity', 0)
                    order.average_fill_price = result.get('fill_price', order.price)
                    order.status = OrderStatus.PARTIALLY_FILLED
                    logger.info(f"Order {order.order_id} partially filled")
                    return
                
                else:
                    # Failed, will retry
                    logger.warning(
                        f"Order {order.order_id} failed: {result.get('reason', 'Unknown')}"
                    )
                    
            except Exception as e:
                logger.error(f"Error executing order {order.order_id}: {e}")
            
            # Wait before retry
            if attempt < max_attempts - 1:
                wait_time = delay * (2 ** attempt) if exponential_backoff else delay
                await asyncio.sleep(wait_time)
        
        # All retries failed
        order.status = OrderStatus.REJECTED
        logger.error(f"Order {order.order_id} failed after {max_attempts} attempts")
    
    async def _place_order(self, order: Order) -> dict:
        """
        Place order on exchange.
        
        Args:
            order: Order to place
            
        Returns:
            Execution result
        """
        # In production, would call exchange API
        # For now, simulate successful execution
        
        logger.info(f"Placing order {order.order_id} on {order.exchange}")
        
        # Simulate random failure (1% chance)
        import random
        if random.random() < 0.01:
            return {
                'status': 'failed',
                'reason': 'Simulated API failure'
            }
        
        return {
            'status': 'success',
            'order_id': order.order_id,
            'fill_price': order.price,
            'filled_quantity': order.quantity
        }
    
    async def monitor_orders(self, order_ids: List[str]):
        """
        Monitor orders until completion or timeout.
        
        Args:
            order_ids: List of order IDs to monitor
        """
        for order_id in order_ids:
            order = self.order_manager.get_order(order_id)
            if not order:
                continue
            
            start_time = datetime.utcnow()
            timeout = timedelta(seconds=self.timeout)
            
            while order.status not in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                elapsed = datetime.utcnow() - start_time
                
                if elapsed > timeout:
                    order.status = OrderStatus.EXPIRED
                    logger.warning(f"Order {order_id} timed out")
                    break
                
                # Simulate waiting for order update
                await asyncio.sleep(1)
    
    async def cancel_orders(self, order_ids: List[str]):
        """Cancel orders."""
        for order_id in order_ids:
            order = self.order_manager.get_order(order_id)
            if order and order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                logger.info(f"Cancelled order {order_id}")
