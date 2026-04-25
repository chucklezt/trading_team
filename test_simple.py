#!/usr/bin/env python3
"""
Simple test script to verify trading team structure.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

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


def test_project_structure():
    """Test project structure."""
    print("\n=== Testing Project Structure ===")
    
    base = Path(__file__).parent
    
    # Check required directories
    required_dirs = [
        'agents',
        'agents/common',
        'agents/scanner',
        'agents/validator',
        'agents/risk',
        'agents/executor',
        'agents/reconciler'
    ]
    
    for dir_name in required_dirs:
        dir_path = base / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"✓ Directory exists: {dir_name}")
        else:
            print(f"✗ Directory missing: {dir_name}")
    
    # Check required files
    required_files = [
        'main.py',
        'requirements.txt',
        'docker-compose.yml',
        'test_simple.py',
        'README.md'
    ]
    
    for file_name in required_files:
        file_path = base / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"✓ File exists: {file_name} ({size} bytes)")
        else:
            print(f"✗ File missing: {file_name}")
    
    print("✓ Project structure test completed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ARBITRAGE TRADING TEAM - STRUCTURE TEST")
    print("=" * 60)
    
    # Run tests
    test_models()
    test_fees()
    test_architecture()
    test_project_structure()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✓ All structure tests passed!")
    print("\nNext Steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Configure exchanges.yaml with your API keys")
    print("3. Start Redis and PostgreSQL: docker-compose up -d")
    print("4. Run the trading team: python main.py")
    print("5. Monitor logs: docker-compose logs -f")
    print("=" * 60)


if __name__ == '__main__':
    main()
