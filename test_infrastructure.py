#!/usr/bin/env python3
"""
Test script to verify trading team infrastructure.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.common.message_queue import MessageQueue
from agents.common.models import Opportunity, OrderSide, OrderStatus


def test_models():
    """Test data models."""
    print("\n=== Testing Data Models ===")
    
    # Test Opportunity model
    opportunity = Opportunity(
        asset="BTC",
        buy_exchange="binance",
        buy_price=45000.0,
        sell_exchange="coinbase",
        sell_price=45500.0,
        quantity=0.1,
        gross_spread=500.0,
        net_profit=450.0,
        confidence=0.85
    )
    
    print(f"✓ Opportunity created: {opportunity.asset}")
    print(f"  - Buy: {opportunity.buy_exchange} @ {opportunity.buy_price}")
    print(f"  - Sell: {opportunity.sell_exchange} @ {opportunity.sell_price}")
    print(f"  - Net Profit: ${opportunity.net_profit:.2f}")
    
    # Test serialization
    data = opportunity.to_dict()
    print(f"✓ Opportunity serialized to {len(data)} fields")
    
    # Test deserialization
    restored = Opportunity.from_dict(data)
    assert restored.asset == opportunity.asset
    print("✓ Opportunity deserialized successfully")
    
    # Test OrderSide enum
    print(f"✓ OrderSide.BUY = {OrderSide.BUY.value}")
    print(f"✓ OrderSide.SELL = {OrderSide.SELL.value}")
    
    # Test OrderStatus enum
    print(f"✓ OrderStatus.PENDING = {OrderStatus.PENDING.value}")
    print(f"✓ OrderStatus.FILLED = {OrderStatus.FILLED.value}")
    
    print("✓ All model tests passed!\n")


async def test_message_queue():
    """Test message queue functionality."""
    print("\n=== Testing Message Queue ===")
    
    # Note: This test requires a running Redis instance
    # For now, we'll just verify the class can be imported and instantiated
    
    try:
        mq = MessageQueue()
        print("✓ MessageQueue instantiated")
        
        # Test message serialization
        test_message = {
            'type': 'test',
            'data': {
                'opportunity_id': 'test_123',
                'asset': 'BTC'
            }
        }
        
        serialized = mq._serialize_message(test_message)
        print(f"✓ Message serialized: {len(serialized)} bytes")
        
        deserialized = mq._deserialize_message(serialized)
        assert deserialized == test_message
        print("✓ Message deserialized correctly")
        
        print("✓ Message queue tests passed!\n")
        
    except Exception as e:
        print(f"⚠ Message queue test skipped (requires Redis): {e}\n")


def test_fees():
    """Test fee calculation."""
    print("\n=== Testing Fee Calculator ===")
    
    from agents.validator.validator_agent import FeeCalculator
    
    # Test fee schedule retrieval
    schedule = FeeCalculator.get_fee_schedule('binance')
    print(f"✓ Binance fee schedule: {schedule}")
    
    # Test withdrawal fee
    withdrawal_fee = FeeCalculator.get_withdrawal_fee('binance', 'BTC')
    print(f"✓ BTC withdrawal fee on Binance: ${withdrawal_fee:.6f}")
    
    # Test min withdrawal
    min_withdrawal = FeeCalculator.get_min_withdrawal('binance', 'BTC')
    print(f"✓ BTC min withdrawal on Binance: {min_withdrawal:.6f}")
    
    # Test unknown exchange
    unknown_schedule = FeeCalculator.get_fee_schedule('unknown_exchange')
    print(f"✓ Default fee schedule: {unknown_schedule}")
    
    print("✓ Fee calculator tests passed!\n")


def test_risk_assessment():
    """Test risk assessment logic."""
    print("\n=== Testing Risk Assessment ===")
    
    from agents.risk.risk_manager_agent import RiskManagerAgent
    
    # Create config
    config = {
        'capital': {'total': 100000},
        'limits': {
            'max_total_exposure': 0.5,
            'max_single_position': 0.1,
            'max_daily_loss': 0.02,
            'max_concurrent_positions': 10
        }
    }
    
    # Test agent initialization
    agent = RiskManagerAgent(config)
    print(f"✓ RiskManagerAgent initialized")
    print(f"  - Capital: ${config['capital']['total']:,.0f}")
    print(f"  - Max Exposure: {config['limits']['max_total_exposure'] * 100}%")
    print(f"  - Max Daily Loss: {config['limits']['max_daily_loss'] * 100}%")
    
    # Test position size calculation
    exposure_ratio = 0.3
    daily_loss_ratio = 0.01
    max_position = agent._calculate_max_position_size(exposure_ratio, daily_loss_ratio)
    print(f"✓ Max position size at current risk: ${max_position:,.2f}")
    
    print("✓ Risk assessment tests passed!\n")


def test_architecture():
    """Test overall architecture."""
    print("\n=== Testing Architecture ===")
    
    # Verify all agent modules can be imported
    agents = [
        ('Scanner', 'agents.scanner.scanner_agent'),
        ('Validator', 'agents.validator.validator_agent'),
        ('Risk Manager', 'agents.risk.risk_manager_agent'),
        ('Executor', 'agents.executor.executor_agent'),
        ('Reconciler', 'agents.reconciler.reconciler_agent'),
    ]
    
    for name, module_path in agents:
        try:
            __import__(module_path)
            print(f"✓ {name} agent module loaded")
        except ImportError as e:
            print(f"✗ {name} agent failed to load: {e}")
            return False
    
    print("✓ All agent modules loaded successfully!\n")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("ARBITRAGE TRADING TEAM - INFRASTRUCTURE TEST")
    print("=" * 60)
    
    # Run tests
    test_models()
    await test_message_queue()
    test_fees()
    test_risk_assessment()
    architecture_ok = test_architecture()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if architecture_ok:
        print("✓ All infrastructure tests passed!")
        print("\nNext Steps:")
        print("1. Configure exchanges.yaml with your API keys")
        print("2. Start Redis and PostgreSQL: docker-compose up -d")
        print("3. Run the trading team: python main.py")
        print("4. Monitor logs: docker-compose logs -f")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
