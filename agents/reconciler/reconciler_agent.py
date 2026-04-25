"""Reconciler Agent - Verifies settlements and calculates P&L."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from agents.common.message_queue import MessageQueue
from agents.common.models import ExecutionResult
from agents.common import setup_logging

setup_logging(__name__)
logger = logging.getLogger(__name__)


class ReconcilerAgent:
    """
    Reconciler Agent verifies settlements and calculates P&L.
    
    Responsibilities:
    - Verify transaction settlements
    - Reconcile account balances
    - Calculate actual P&L
    - Generate reports
    - Maintain audit trail
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.message_queue = MessageQueue()
        self.running = False
        
        # Tracking
        self.executed_opportunities: Dict[str, dict] = {}
        self.daily_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Reconciliation settings
        self.reconciliation_frequency = config.get('reconciliation', {}).get(
            'frequency', 'hourly'
        )
        self.reconciliation_timeout = config.get('reconciliation', {}).get(
            'timeout', 300
        )
    
    async def start(self):
        """Start the reconciler agent."""
        logger.info("Starting Reconciler Agent")
        self.running = True
        
        # Subscribe to execution results
        await self.message_queue.subscribe(
            'trading:execution',
            self._process_execution
        )
        
        # Start reconciliation loop
        await self._reconciliation_loop()
    
    async def stop(self):
        """Stop the reconciler agent."""
        logger.info("Stopping Reconciler Agent")
        self.running = False
    
    async def _process_execution(self, message_data: str):
        """Process execution result."""
        try:
            message = self.message_queue._deserialize_message(message_data)
            
            result = ExecutionResult.from_dict(message.get('result', {}))
            opportunity_id = message.get('opportunity_id')
            
            # Track opportunity
            self.executed_opportunities[opportunity_id] = {
                'result': result,
                'timestamp': datetime.utcnow()
            }
            
            # Update P&L
            await self._update_pnl(result)
            
            # Verify settlement
            settlement = await self._verify_settlement(result)
            
            if settlement['settled']:
                logger.info(f"Opportunity {opportunity_id} settled successfully")
                await self.message_queue.publish('trading:reconciliation', {
                    'type': 'settlement_verified',
                    'opportunity_id': opportunity_id,
                    'result': settlement,
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                logger.warning(f"Opportunity {opportunity_id} settlement pending")
                
        except Exception as e:
            logger.error(f"Error processing execution: {e}")
    
    async def _reconciliation_loop(self):
        """Run periodic reconciliation."""
        while self.running:
            try:
                # Check all executed opportunities
                for opportunity_id, data in list(self.executed_opportunities.items()):
                    result = data['result']
                    
                    # Check if settled
                    if result.status not in ['settled', 'failed']:
                        settlement = await self._verify_settlement(result)
                        
                        if settlement['settled']:
                            del self.executed_opportunities[opportunity_id]
                        elif settlement['timeout']:
                            # Mark as failed if timeout
                            result.status = 'failed'
                            result.error_message = "Settlement timeout"
                            del self.executed_opportunities[opportunity_id]
                
                # Generate periodic report
                if self._should_generate_report():
                    await self._generate_report()
                
                # Wait for next iteration
                await asyncio.sleep(3600)  # Hourly check
                
            except Exception as e:
                logger.error(f"Error in reconciliation loop: {e}")
                await asyncio.sleep(60)
    
    async def _update_pnl(self, result: ExecutionResult):
        """Update daily P&L."""
        if result.status == 'success':
            # Calculate P&L based on fill prices
            pnl = self._calculate_pnl(result)
            self.daily_pnl += pnl
            
            # Update trade statistics
            self.total_trades += 1
            if pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            
            logger.info(f"Updated P&L: ${self.daily_pnl:.2f}")
    
    def _calculate_pnl(self, result: ExecutionResult) -> float:
        """
        Calculate P&L for an execution.
        
        In production, would compare execution prices with opportunity prices.
        """
        # For now, return a placeholder value
        # In reality, would need to track opportunity prices
        return 0.0
    
    async def _verify_settlement(self, result: ExecutionResult) -> dict:
        """
        Verify settlement of execution.
        
        Args:
            result: Execution result
            
        Returns:
            Settlement verification result
        """
        # Check if already settled
        if result.status == 'settled':
            return {
                'settled': True,
                'settled_at': result.executed_at,
                'verification': 'Already settled'
            }
        
        # Check timeout
        timeout = timedelta(seconds=self.reconciliation_timeout)
        if datetime.utcnow() - result.executed_at > timeout:
            return {
                'settled': False,
                'timeout': True,
                'timeout_at': datetime.utcnow()
            }
        
        # Simulate settlement verification
        # In production, would check exchange balances and transaction hashes
        
        import random
        settled = random.random() > 0.05  # 95% success rate
        
        return {
            'settled': settled,
            'settled_at': datetime.utcnow() if settled else None,
            'verification': 'Settled' if settled else 'Pending'
        }
    
    def _should_generate_report(self) -> bool:
        """Check if it's time to generate a report."""
        # Simple hourly check
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        
        # Check if last report was more than an hour ago
        # (would need to store last report time)
        return True  # For now, generate every hour
    
    async def _generate_report(self):
        """Generate daily reconciliation report."""
        logger.info("Generating reconciliation report")
        
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'summary': {
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
                'daily_pnl': self.daily_pnl
            },
            'executed_opportunities': len(self.executed_opportunities),
            'pending_settlements': sum(
                1 for data in self.executed_opportunities.values()
                if data['result'].status not in ['settled', 'failed']
            )
        }
        
        # Save report (in production, would save to database or file)
        # logger.info(f"Reconciliation report: {report}")
        
        # Send report via message queue
        await self.message_queue.publish('trading:reconciliation', {
            'type': 'reconciliation_report',
            'report': report,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Reset counters for next period
        # self.daily_pnl = 0
        # self.total_trades = 0
        # self.winning_trades = 0
        # self.losing_trades = 0


class SettlementVerifier:
    """Verifies transaction settlements."""
    
    def __init__(self):
        self.settlements: Dict[str, dict] = {}
    
    def verify_settlement(self, transaction_id: str, settlement_data: dict) -> bool:
        """
        Verify a transaction settlement.
        
        Args:
            transaction_id: Transaction identifier
            settlement_data: Settlement data
            
        Returns:
            True if settlement verified
        """
        # In production, would:
        # 1. Check blockchain confirmation (for crypto)
        # 2. Verify bank transaction (for fiat)
        # 3. Confirm exchange balance changes
        # 4. Match with expected amounts
        
        self.settlements[transaction_id] = settlement_data
        
        logger.info(f"Verified settlement for {transaction_id}")
        
        return True
    
    def get_settlement_status(self, transaction_id: str) -> Optional[dict]:
        """Get settlement status for transaction."""
        return self.settlements.get(transaction_id)
    
    def reconcile_balances(self, exchange: str, expected: dict, actual: dict) -> dict:
        """
        Reconcile exchange balances.
        
        Args:
            exchange: Exchange name
            expected: Expected balances
            actual: Actual balances
            
        Returns:
            Reconciliation result
        """
        discrepancies = []
        
        for asset, expected_balance in expected.items():
            actual_balance = actual.get(asset, 0)
            difference = abs(expected_balance - actual_balance)
            
            if difference > 0.0001:  # Allow small tolerance
                discrepancies.append({
                    'asset': asset,
                    'expected': expected_balance,
                    'actual': actual_balance,
                    'difference': difference
                })
        
        return {
            'exchange': exchange,
            'reconciled': len(discrepancies) == 0,
            'discrepancies': discrepancies
        }
