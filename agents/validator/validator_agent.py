"""Validator Agent - Validates arbitrage opportunities."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from agents.common.models import Opportunity, OpportunityStatus
from agents.common import setup_logging

# Optional dependency
try:
    from agents.common.message_queue import MessageQueue
except ImportError:
    MessageQueue = None

setup_logging(__name__)
logger = logging.getLogger(__name__)


class FeeCalculator:
    """Calculate trading fees for exchanges."""
    
    FEE_SCHEDULES = {
        'binance': {'maker': 0.001, 'taker': 0.001},
        'coinbase': {'maker': 0.005, 'taker': 0.005},
        'kraken': {'maker': 0.0016, 'taker': 0.0026},
    }
    
    WITHDRAWAL_FEES = {
        'binance': {'BTC': 0.0002, 'ETH': 0.001},
        'coinbase': {'BTC': 0.0001, 'ETH': 0.001},
    }
    
    MIN_WITHDRAWALS = {
        'binance': {'BTC': 0.0005, 'ETH': 0.01},
        'coinbase': {'BTC': 0.001, 'ETH': 0.01},
    }
    
    @classmethod
    def get_fee_schedule(cls, exchange: str) -> Dict[str, float]:
        """Get fee schedule for exchange."""
        return cls.FEE_SCHEDULES.get(exchange, {'maker': 0.005, 'taker': 0.005})
    
    @classmethod
    def get_withdrawal_fee(cls, exchange: str, asset: str) -> float:
        """Get withdrawal fee for asset on exchange."""
        fees = cls.WITHDRAWAL_FEES.get(exchange, {})
        return fees.get(asset, 0.0)
    
    @classmethod
    def get_min_withdrawal(cls, exchange: str, asset: str) -> float:
        """Get minimum withdrawal amount."""
        min_w = cls.MIN_WITHDRAWALS.get(exchange, {})
        return min_w.get(asset, 0.01)


class ValidatorAgent:
    """
    Validator Agent validates arbitrage opportunities.
    
    Responsibilities:
    - Check liquidity availability
    - Calculate accurate net profit after fees
    - Verify settlement feasibility
    - Detect false positives
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.message_queue = MessageQueue()
        self.running = False
    
    async def start(self):
        """Start the validator agent."""
        logger.info("Starting Validator Agent")
        self.running = True
        await self._subscribe_and_process()
    
    async def stop(self):
        """Stop the validator agent."""
        logger.info("Stopping Validator Agent")
        self.running = False
    
    async def _subscribe_and_process(self):
        """Subscribe to opportunities and validate them."""
        await self.message_queue.subscribe(
            'trading:opportunities',
            self._process_opportunity
        )
    
    async def _process_opportunity(self, message_data: str):
        """Process incoming opportunity message."""
        try:
            message = self.message_queue._deserialize_message(message_data)
            
            # Create opportunity object
            opportunity = Opportunity.from_dict(message.get('data', {}))
            
            # Validate opportunity
            validation = await self.validate(opportunity)
            
            # Send result to risk manager
            await self.message_queue.send_validation_result(
                opportunity.asset,
                validation.to_dict()
            )
            
        except Exception as e:
            logger.error(f"Error processing opportunity: {e}")
    
    async def validate(self, opportunity: Opportunity) -> 'ValidationResult':
        """
        Validate an arbitrage opportunity.
        
        Args:
            opportunity: Opportunity to validate
            
        Returns:
            ValidationResult with validation details
        """
        logger.info(f"Validating opportunity: {opportunity.asset}")
        
        # Check liquidity
        liquidity_check = await self._check_liquidity(opportunity)
        
        if not liquidity_check['valid']:
            return ValidationResult(
                opportunity_id=opportunity.asset,
                valid=False,
                reason="Insufficient liquidity",
                details=liquidity_check
            )
        
        # Calculate net profit
        net_profit = await self._calculate_net_profit(opportunity)
        
        if net_profit <= 0:
            return ValidationResult(
                opportunity_id=opportunity.asset,
                valid=False,
                reason="No profitable spread after fees",
                net_profit=net_profit,
                details={'net_profit': net_profit}
            )
        
        # Check settlement feasibility
        settlement_check = await self._check_settlement(opportunity)
        
        if not settlement_check['valid']:
            return ValidationResult(
                opportunity_id=opportunity.asset,
                valid=False,
                reason="Settlement not feasible",
                details=settlement_check
            )
        
        return ValidationResult(
            opportunity_id=opportunity.asset,
            valid=True,
            net_profit=net_profit,
            details={
                'liquidity': liquidity_check,
                'net_profit': net_profit,
                'settlement': settlement_check
            }
        )
    
    async def _check_liquidity(self, opportunity: Opportunity) -> dict:
        """
        Check if there's sufficient liquidity for the trade.
        
        Args:
            opportunity: Opportunity to check
            
        Returns:
            Liquidity check result
        """
        min_buy_volume = self.config.get('liquidity_checks', {}).get(
            'min_buy_volume', 0.05
        )
        min_sell_volume = self.config.get('liquidity_checks', {}).get(
            'min_sell_volume', 0.05
        )
        
        buy_liquidity_ok = opportunity.quantity >= min_buy_volume
        sell_liquidity_ok = opportunity.quantity >= min_sell_volume
        
        return {
            'valid': buy_liquidity_ok and sell_liquidity_ok,
            'buy_liquidity_ok': buy_liquidity_ok,
            'sell_liquidity_ok': sell_liquidity_ok,
            'required_buy_volume': min_buy_volume,
            'required_sell_volume': min_sell_volume,
            'available_buy_volume': opportunity.quantity,
            'available_sell_volume': opportunity.quantity
        }
    
    async def _calculate_net_profit(self, opportunity: Opportunity) -> float:
        """
        Calculate net profit after all fees.
        
        Args:
            opportunity: Opportunity to calculate
            
        Returns:
            Net profit in USD
        """
        buy_exchange = opportunity.buy_exchange
        sell_exchange = opportunity.sell_exchange
        
        # Get fee schedules
        buy_fee_rate = FeeCalculator.get_fee_schedule(buy_exchange)['maker']
        sell_fee_rate = FeeCalculator.get_fee_schedule(sell_exchange)['maker']
        
        # Calculate trading fees
        buy_fee = opportunity.quantity * opportunity.buy_price * buy_fee_rate
        sell_fee = opportunity.quantity * opportunity.sell_price * sell_fee_rate
        
        # Calculate withdrawal fee
        asset = opportunity.asset
        withdrawal_fee = FeeCalculator.get_withdrawal_fee(
            buy_exchange, asset
        )
        
        # Total fees
        total_fees = buy_fee + sell_fee + withdrawal_fee
        
        # Gross profit
        gross_profit = (
            opportunity.quantity * opportunity.sell_price -
            opportunity.quantity * opportunity.buy_price
        )
        
        # Net profit
        net_profit = gross_profit - total_fees
        
        logger.debug(
            f"Net profit calculation for {opportunity.asset}: "
            f"Gross: ${gross_profit:.2f}, Fees: ${total_fees:.2f}, "
            f"Net: ${net_profit:.2f}"
        )
        
        return net_profit
    
    async def _check_settlement(self, opportunity: Opportunity) -> dict:
        """
        Check if settlement is feasible within constraints.
        
        Args:
            opportunity: Opportunity to check
            
        Returns:
            Settlement check result
        """
        max_settlement_time = self.config.get('settlement', {}).get(
            'max_settlement_time', 24
        )
        
        # Check withdrawal times
        buy_exchange = opportunity.buy_exchange
        sell_exchange = opportunity.sell_exchange
        
        # Typical withdrawal times (in minutes)
        withdrawal_times = {
            'binance': 10,
            'coinbase': 15,
            'kraken': 20
        }
        
        buy_withdrawal_time = withdrawal_times.get(buy_exchange, 30)
        sell_withdrawal_time = withdrawal_times.get(sell_exchange, 30)
        
        total_settlement_time = buy_withdrawal_time + sell_withdrawal_time
        
        valid = total_settlement_time <= max_settlement_time * 60  # Convert to minutes
        
        return {
            'valid': valid,
            'buy_withdrawal_time_minutes': buy_withdrawal_time,
            'sell_withdrawal_time_minutes': sell_withdrawal_time,
            'total_settlement_time_minutes': total_settlement_time,
            'max_allowed_minutes': max_settlement_time * 60
        }


class ValidationResult:
    """Validation result for an opportunity."""
    
    def __init__(self, opportunity_id: str, valid: bool, reason: str = "",
                 net_profit: float = 0.0, details: dict = None):
        self.opportunity_id = opportunity_id
        self.valid = valid
        self.reason = reason
        self.net_profit = net_profit
        self.details = details or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'opportunity_id': self.opportunity_id,
            'valid': self.valid,
            'reason': self.reason,
            'net_profit': self.net_profit,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }
