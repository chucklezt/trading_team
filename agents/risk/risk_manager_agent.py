"""Risk Manager Agent - Assesses and enforces risk limits."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from agents.common.message_queue import MessageQueue
from agents.common.models import Opportunity, RiskAssessment
from agents.common import setup_logging

setup_logging(__name__)
logger = logging.getLogger(__name__)


class RiskManagerAgent:
    """
    Risk Manager Agent assesses risk and enforces limits.
    
    Responsibilities:
    - Monitor total exposure
    - Enforce position limits
    - Calculate risk metrics
    - Approve or reject opportunities
    - Implement emergency stop procedures
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.message_queue = MessageQueue()
        self.running = False
        
        # Risk limits
        self.capital = config.get('capital', {}).get('total', 100000)
        self.max_exposure = config.get('limits', {}).get('max_total_exposure', 0.5)
        self.max_single_position = config.get('limits', {}).get('max_single_position', 0.1)
        self.max_daily_loss = config.get('limits', {}).get('max_daily_loss', 0.02)
        self.max_concurrent_positions = config.get('limits', {}).get('max_concurrent_positions', 10)
        
        # State tracking
        self.current_exposure = 0.0
        self.daily_pnl = 0.0
        self.active_positions: List[dict] = []
        self.open_orders: List[dict] = []
        self.daily_trading_volume = 0.0
        self.recent_failures: List[datetime] = []
        
        # Emergency state
        self.emergency_level = 0  # 0 = normal, 1 = level 1, 2 = level 2, 3 = stopped
    
    async def start(self):
        """Start the risk manager agent."""
        logger.info("Starting Risk Manager Agent")
        self.running = True
        self._reset_daily_metrics()
        
        # Subscribe to messages
        await self.message_queue.subscribe(
            'trading:opportunities',
            self._process_opportunity
        )
        await self.message_queue.subscribe(
            'trading:validation_result',
            self._process_validation
        )
        
        # Start monitoring loop
        await self._monitor_loop()
    
    async def stop(self):
        """Stop the risk manager agent."""
        logger.info("Stopping Risk Manager Agent")
        self.running = False
        await self._trigger_emergency_stop()
    
    async def _monitor_loop(self):
        """Monitor risk metrics continuously."""
        while self.running:
            try:
                await self._update_metrics()
                await self._check_emergency_conditions()
                
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(30)
    
    async def _process_opportunity(self, message_data: str):
        """Process opportunity before risk assessment."""
        try:
            message = self.message_queue._deserialize_message(message_data)
            
            # For now, just pass through to risk assessment
            # In production, would validate message structure
            await self.message_queue.publish(
                'trading:risk',
                message_data
            )
        except Exception as e:
            logger.error(f"Error processing opportunity: {e}")
    
    async def _process_validation(self, message_data: str):
        """Process validated opportunity."""
        try:
            message = self.message_queue._deserialize_message(message_data)
            
            validation_result = message.get('result', {})
            opportunity_id = message.get('opportunity_id')
            
            # If valid, assess risk
            if validation_result.get('valid', False):
                assessment = await self.assess_risk(
                    opportunity_id,
                    validation_result.get('net_profit', 0)
                )
                
                # Send to executor
                await self.message_queue.send_risk_assessment(
                    opportunity_id,
                    assessment.to_dict()
                )
                
            else:
                # Reject opportunity
                await self.message_queue.publish('trading:execution', {
                    'type': 'risk_rejection',
                    'opportunity_id': opportunity_id,
                    'reason': 'Risk limits exceeded',
                    'timestamp': datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error processing validation: {e}")
    
    async def assess_risk(self, opportunity_id: str, net_profit: float) -> RiskAssessment:
        """
        Assess risk for an opportunity.
        
        Args:
            opportunity_id: Opportunity identifier
            net_profit: Expected net profit
            
        Returns:
            RiskAssessment with approval decision
        """
        logger.info(f"Assessing risk for {opportunity_id}")
        
        # Calculate current ratios
        exposure_ratio = self.current_exposure / self.capital if self.capital > 0 else 0
        daily_loss_ratio = abs(self.daily_pnl) / self.capital if self.capital > 0 else 0
        position_size_ratio = net_profit / self.capital if self.capital > 0 else 0
        
        # Check against limits
        exposure_ok = exposure_ratio + position_size_ratio <= self.max_exposure
        daily_loss_ok = daily_loss_ratio + position_size_ratio <= self.max_daily_loss
        position_count_ok = len(self.active_positions) < self.max_concurrent_positions
        
        # Calculate overall risk score (0-1, lower is better)
        risk_score = (
            exposure_ratio * 0.4 +
            daily_loss_ratio * 0.3 +
            position_size_ratio * 0.2 +
            (1 - position_count_ok) * 0.1
        )
        
        # Determine approval
        approved = (
            exposure_ok and
            daily_loss_ok and
            position_count_ok and
            risk_score < 0.8  # 80% threshold
        )
        
        # Calculate maximum position size
        max_position_size = self._calculate_max_position_size(
            exposure_ratio, daily_loss_ratio
        )
        
        # Generate recommendations
        recommendations = []
        if not exposure_ok:
            recommendations.append("Reduce overall exposure before proceeding")
        if not daily_loss_ok:
            recommendations.append("Daily loss limit approaching, consider reducing position size")
        if not position_count_ok:
            recommendations.append("Maximum concurrent positions reached")
        if risk_score > 0.6:
            recommendations.append("High risk score, proceed with caution")
        
        assessment = RiskAssessment(
            opportunity_id=opportunity_id,
            exposure_ratio=exposure_ratio,
            daily_loss_ratio=daily_loss_ratio,
            position_size_ratio=position_size_ratio,
            risk_score=risk_score,
            approved=approved,
            max_position_size=max_position_size,
            recommendations=recommendations
        )
        
        logger.info(
            f"Risk assessment for {opportunity_id}: "
            f"Risk score: {risk_score:.2f}, Approved: {approved}"
        )
        
        return assessment
    
    def _calculate_max_position_size(self, exposure_ratio: float, daily_loss_ratio: float) -> float:
        """Calculate maximum allowed position size based on current risk."""
        base_max = self.max_single_position * self.capital
        
        # Reduce max position if risk is high
        if exposure_ratio > 0.4:
            reduction = 0.5
        elif exposure_ratio > 0.3:
            reduction = 0.3
        else:
            reduction = 0
        
        if daily_loss_ratio > 0.015:
            reduction += 0.2
        
        return base_max * (1 - reduction)
    
    async def _update_metrics(self):
        """Update current risk metrics."""
        # Update exposure
        self.current_exposure = sum(
            pos.get('value', 0) for pos in self.active_positions
        )
        
        # Update daily P&L
        self.daily_pnl = await self._get_daily_pnl()
        
        # Update trading volume
        self.daily_trading_volume = await self._get_daily_trading_volume()
        
        # Update failure count
        self._update_failure_count()
    
    async def _get_daily_pnl(self) -> float:
        """Get daily P&L (placeholder)."""
        # In production, would query database for actual P&L
        return self.daily_pnl
    
    async def _get_daily_trading_volume(self) -> float:
        """Get daily trading volume (placeholder)."""
        return self.daily_trading_volume
    
    def _update_failure_count(self):
        """Update count of recent failures."""
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)
        
        # Remove old failures
        self.recent_failures = [
            f for f in self.recent_failures
            if f > one_minute_ago
        ]
        
        # Add new failure
        self.recent_failures.append(now)
    
    async def _check_emergency_conditions(self):
        """Check for emergency stop conditions."""
        daily_loss_ratio = abs(self.daily_pnl) / self.capital if self.capital > 0 else 0
        
        # Level 3: Critical
        if daily_loss_ratio > 0.05 or self.emergency_level == 3:
            await self._trigger_emergency_stop(3, "Daily loss exceeded 5%")
            return
        
        # Level 2: High
        if daily_loss_ratio > 0.02 or self.emergency_level == 2:
            await self._trigger_emergency_stop(2, "Daily loss exceeded 2%")
            return
        
        # Level 1: Warning
        if daily_loss_ratio > 0.01 or self.emergency_level == 1:
            await self._trigger_emergency_stop(1, "Daily loss exceeded 1%")
            return
        
        # Check failure rate
        if len(self.recent_failures) >= 10:
            await self._trigger_emergency_stop(1, "High failure rate detected")
    
    async def _trigger_emergency_stop(self, level: int, reason: str):
        """Trigger emergency stop procedure."""
        logger.critical(f"EMERGENCY STOP: Level {level} - {reason}")
        
        self.emergency_level = level
        
        # Send alert
        await self.message_queue.broadcast_alert(
            'emergency_stop',
            f"Emergency stop triggered: Level {level} - {reason}",
            'critical'
        )
        
        # Take action based on level
        if level == 3:
            await self._emergency_shutdown()
        elif level == 2:
            await self._stop_all_trading()
        elif level == 1:
            await self._reduce_trading_volume()
    
    async def _emergency_shutdown(self):
        """Emergency shutdown procedure."""
        logger.critical("EMERGENCY SHUTDOWN initiated")
        
        # Close all positions
        await self._close_all_positions()
        
        # Freeze accounts
        await self._freeze_accounts()
        
        # Stop all agents
        await self._stop_all_agents()
        
        # Notify stakeholders
        await self._notify_stakeholders()
    
    async def _stop_all_trading(self):
        """Stop all trading."""
        logger.error("Stopping all trading")
        
        # Stop accepting new opportunities
        await self.message_queue.publish('trading:opportunities', {
            'type': 'trading_paused',
            'reason': 'Emergency stop level 2',
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Close all open positions
        await self._close_all_positions()
    
    async def _reduce_trading_volume(self):
        """Reduce trading volume by 50%."""
        logger.warning("Reducing trading volume by 50%")
        
        # Implement volume reduction logic
        pass
    
    async def _close_all_positions(self):
        """Close all open positions."""
        logger.info("Closing all positions")
        
        for position in self.active_positions:
            try:
                # Send close order to executor
                await self.message_queue.publish('trading:execution', {
                    'type': 'close_position',
                    'position_id': position.get('position_id'),
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error closing position {position}: {e}")
        
        self.active_positions = []
    
    async def _freeze_accounts(self):
        """Freeze all trading accounts."""
        logger.info("Freezing all accounts")
        
        # Implement account freezing logic
        pass
    
    async def _stop_all_agents(self):
        """Stop all trading agents."""
        logger.info("Stopping all agents")
        
        # Send stop signal to all agents
        await self.message_queue.broadcast_alert(
            'stop_all_agents',
            'Emergency stop: All agents should stop immediately',
            'critical'
        )
    
    async def _notify_stakeholders(self):
        """Notify stakeholders of emergency."""
        logger.info("Notifying stakeholders")
        
        # Send notification (email, Slack, etc.)
        pass
