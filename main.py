#!/usr/bin/env python3
"""
Arbitrage Trading Team - Main Entry Point

This script starts all trading agents and coordinates their operation.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/trading.log')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


class TradingTeam:
    """
    Orchestrates all trading agents.
    """
    
    def __init__(self, config_path: str = 'config'):
        self.config_path = Path(config_path)
        self.agents = {}
        self.running = False
    
    async def start(self):
        """Start all agents."""
        logger.info("Starting Arbitrage Trading Team")
        self.running = True
        
        # Load configuration
        config = self._load_config()
        
        # Start each agent
        agents_config = config.get('agents', {})
        
        # Start Scanner Agent
        if 'scanner' in agents_config:
            scanner = ScannerAgent(agents_config['scanner'])
            self.agents['scanner'] = scanner
            await scanner.start()
            logger.info("Scanner Agent started")
        
        # Start Validator Agent
        if 'validator' in agents_config:
            validator = ValidatorAgent(agents_config['validator'])
            self.agents['validator'] = validator
            await validator.start()
            logger.info("Validator Agent started")
        
        # Start Risk Manager Agent
        if 'risk' in agents_config:
            risk_manager = RiskManagerAgent(agents_config['risk'])
            self.agents['risk'] = risk_manager
            await risk_manager.start()
            logger.info("Risk Manager Agent started")
        
        # Start Executor Agent
        if 'executor' in agents_config:
            executor = ExecutorAgent(agents_config['executor'])
            self.agents['executor'] = executor
            await executor.start()
            logger.info("Executor Agent started")
        
        # Start Reconciler Agent
        if 'reconciler' in agents_config:
            reconciler = ReconcilerAgent(agents_config['reconciler'])
            self.agents['reconciler'] = reconciler
            await reconciler.start()
            logger.info("Reconciler Agent started")
        
        logger.info("All agents started successfully")
    
    async def stop(self):
        """Stop all agents gracefully."""
        logger.info("Stopping Arbitrage Trading Team")
        self.running = False
        
        # Stop each agent
        for name, agent in self.agents.items():
            try:
                await agent.stop()
                logger.info(f"Agent {name} stopped")
            except Exception as e:
                logger.error(f"Error stopping agent {name}: {e}")
        
        logger.info("All agents stopped")
    
    def _load_config(self) -> dict:
        """Load configuration from files."""
        config = {
            'agents': {
                'scanner': {
                    'exchanges': self._load_exchanges_config(),
                    'thresholds': {
                        'min_spread_percentage': 0.1,
                        'max_spread_percentage': 5.0
                    }
                },
                'validator': {
                    'liquidity_checks': {
                        'min_buy_volume': 0.05,
                        'min_sell_volume': 0.05
                    },
                    'settlement': {
                        'max_settlement_time': 24
                    }
                },
                'risk': {
                    'capital': {
                        'total': float(os.environ.get('TRADING_CAPITAL', 100000))
                    },
                    'limits': {
                        'max_total_exposure': 0.5,
                        'max_single_position': 0.1,
                        'max_daily_loss': 0.02,
                        'max_concurrent_positions': 10
                    }
                },
                'executor': {
                    'timeout': {
                        'order_timeout': 60
                    },
                    'retry': {
                        'max_attempts': 3,
                        'initial_delay': 5
                    }
                },
                'reconciler': {
                    'reconciliation': {
                        'frequency': 'hourly',
                        'timeout': 300
                    }
                }
            }
        }
        
        # Load exchanges configuration
        exchanges_file = self.config_path / 'exchanges.yaml'
        if exchanges_file.exists():
            try:
                import yaml
                exchanges_config = yaml.safe_load(exchanges_file.read_text())
                if exchanges_config:
                    config['agents']['scanner']['exchanges'] = exchanges_config
            except Exception as e:
                logger.warning(f"Could not load exchanges config: {e}")
        
        return config


class ScannerAgent:
    """Scanner Agent wrapper."""
    
    def __init__(self, config: dict):
        self.config = config
        self.agent = None
    
    async def start(self):
        """Start scanner agent."""
        from agents.scanner.scanner_agent import ScannerAgent as ScannerAgentImpl
        self.agent = ScannerAgentImpl(self.config)
        await self.agent.start()
    
    async def stop(self):
        """Stop scanner agent."""
        if self.agent:
            await self.agent.stop()


class ValidatorAgent:
    """Validator Agent wrapper."""
    
    def __init__(self, config: dict):
        self.config = config
        self.agent = None
    
    async def start(self):
        """Start validator agent."""
        from agents.validator.validator_agent import ValidatorAgent as ValidatorAgentImpl
        self.agent = ValidatorAgentImpl(self.config)
        await self.agent.start()
    
    async def stop(self):
        """Stop validator agent."""
        if self.agent:
            await self.agent.stop()


class RiskManagerAgent:
    """Risk Manager Agent wrapper."""
    
    def __init__(self, config: dict):
        self.config = config
        self.agent = None
    
    async def start(self):
        """Start risk manager agent."""
        from agents.risk.risk_manager_agent import RiskManagerAgent as RiskManagerAgentImpl
        self.agent = RiskManagerAgentImpl(self.config)
        await self.agent.start()
    
    async def stop(self):
        """Stop risk manager agent."""
        if self.agent:
            await self.agent.stop()


class ExecutorAgent:
    """Executor Agent wrapper."""
    
    def __init__(self, config: dict):
        self.config = config
        self.agent = None
    
    async def start(self):
        """Start executor agent."""
        from agents.executor.executor_agent import ExecutorAgent as ExecutorAgentImpl
        self.agent = ExecutorAgentImpl(self.config)
        await self.agent.start()
    
    async def stop(self):
        """Stop executor agent."""
        if self.agent:
            await self.agent.stop()


class ReconcilerAgent:
    """Reconciler Agent wrapper."""
    
    def __init__(self, config: dict):
        self.config = config
        self.agent = None
    
    async def start(self):
        """Start reconciler agent."""
        from agents.reconciler.reconciler_agent import ReconcilerAgent as ReconcilerAgentImpl
        self.agent = ReconcilerAgentImpl(self.config)
        await self.agent.start()
    
    async def stop(self):
        """Stop reconciler agent."""
        if self.agent:
            await self.agent.stop()


async def main():
    """Main entry point."""
    logger.info("Arbitrage Trading Team v1.0")
    logger.info("Starting trading team...")
    
    # Create trading team
    team = TradingTeam('config')
    
    try:
        # Start all agents
        await team.start()
        
        # Keep running (would normally monitor and handle signals)
        logger.info("Trading team is running. Press Ctrl+C to stop.")
        
        # In production, would handle signals and graceful shutdown
        # For now, just run for a while
        await asyncio.sleep(3600)  # Run for 1 hour
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    finally:
        # Stop all agents
        await team.stop()
        logger.info("Trading team stopped")


if __name__ == '__main__':
    asyncio.run(main())
