"""Data models for trading system."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class OpportunityStatus(Enum):
    """Status of an arbitrage opportunity."""
    DETECTED = "detected"
    VALIDATED = "validated"
    REJECTED = "rejected"
    EXECUTED = "executed"
    SETTLED = "settled"
    FAILED = "failed"


class OrderSide(Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Opportunity:
    """
    Arbitrage opportunity data model.
    
    Represents a price discrepancy between two exchanges or markets.
    """
    asset: str
    buy_exchange: str
    buy_price: float
    sell_exchange: str
    sell_price: float
    quantity: float
    gross_spread: float
    net_profit: float
    confidence: float
    status: OpportunityStatus = OpportunityStatus.DETECTED
    created_at: datetime = field(default_factory=datetime.utcnow)
    validated_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'asset': self.asset,
            'buy_exchange': self.buy_exchange,
            'buy_price': self.buy_price,
            'sell_exchange': self.sell_exchange,
            'sell_price': self.sell_price,
            'quantity': self.quantity,
            'gross_spread': self.gross_spread,
            'net_profit': self.net_profit,
            'confidence': self.confidence,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'validated_at': self.validated_at.isoformat() if self.validated_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'settled_at': self.settled_at.isoformat() if self.settled_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Opportunity':
        """Create from dictionary."""
        return cls(
            asset=data['asset'],
            buy_exchange=data['buy_exchange'],
            buy_price=data['buy_price'],
            sell_exchange=data['sell_exchange'],
            sell_price=data['sell_price'],
            quantity=data['quantity'],
            gross_spread=data['gross_spread'],
            net_profit=data['net_profit'],
            confidence=data['confidence'],
            status=OpportunityStatus(data.get('status', 'detected')),
            created_at=datetime.fromisoformat(data['created_at']),
            validated_at=datetime.fromisoformat(data['validated_at']) if data.get('validated_at') else None,
            executed_at=datetime.fromisoformat(data['executed_at']) if data.get('executed_at') else None,
            settled_at=datetime.fromisoformat(data['settled_at']) if data.get('settled_at') else None
        )


@dataclass
class Position:
    """
    Trading position data model.
    
    Represents an open position on an exchange.
    """
    position_id: str
    opportunity_id: str
    exchange: str
    symbol: str
    side: OrderSide
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    status: str = "open"
    opened_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'position_id': self.position_id,
            'opportunity_id': self.opportunity_id,
            'exchange': self.exchange,
            'symbol': self.symbol,
            'side': self.side.value,
            'size': self.size,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'unrealized_pnl': self.unrealized_pnl,
            'status': self.status,
            'opened_at': self.opened_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Position':
        """Create from dictionary."""
        return cls(
            position_id=data['position_id'],
            opportunity_id=data['opportunity_id'],
            exchange=data['exchange'],
            symbol=data['symbol'],
            side=OrderSide(data['side']),
            size=data['size'],
            entry_price=data['entry_price'],
            current_price=data['current_price'],
            unrealized_pnl=data['unrealized_pnl'],
            status=data.get('status', 'open'),
            opened_at=datetime.fromisoformat(data['opened_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )


@dataclass
class Order:
    """
    Order data model.
    
    Represents an order placed on an exchange.
    """
    order_id: str
    opportunity_id: str
    position_id: str
    exchange: str
    symbol: str
    side: OrderSide
    order_type: str
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_fill_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'order_id': self.order_id,
            'opportunity_id': self.opportunity_id,
            'position_id': self.position_id,
            'exchange': self.exchange,
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type,
            'quantity': self.quantity,
            'price': self.price,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'average_fill_price': self.average_fill_price,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Order':
        """Create from dictionary."""
        return cls(
            order_id=data['order_id'],
            opportunity_id=data['opportunity_id'],
            position_id=data['position_id'],
            exchange=data['exchange'],
            symbol=data['symbol'],
            side=OrderSide(data['side']),
            order_type=data['order_type'],
            quantity=data['quantity'],
            price=data.get('price'),
            status=OrderStatus(data.get('status', 'pending')),
            filled_quantity=data.get('filled_quantity', 0.0),
            average_fill_price=data.get('average_fill_price', 0.0),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )


@dataclass
class RiskAssessment:
    """
    Risk assessment data model.
    
    Contains risk metrics and approval decision.
    """
    opportunity_id: str
    exposure_ratio: float
    daily_loss_ratio: float
    position_size_ratio: float
    risk_score: float
    approved: bool
    max_position_size: float
    recommendations: list = field(default_factory=list)
    assessed_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'opportunity_id': self.opportunity_id,
            'exposure_ratio': self.exposure_ratio,
            'daily_loss_ratio': self.daily_loss_ratio,
            'position_size_ratio': self.position_size_ratio,
            'risk_score': self.risk_score,
            'approved': self.approved,
            'max_position_size': self.max_position_size,
            'recommendations': self.recommendations,
            'assessed_at': self.assessed_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RiskAssessment':
        """Create from dictionary."""
        return cls(
            opportunity_id=data['opportunity_id'],
            exposure_ratio=data['exposure_ratio'],
            daily_loss_ratio=data['daily_loss_ratio'],
            position_size_ratio=data['position_size_ratio'],
            risk_score=data['risk_score'],
            approved=data['approved'],
            max_position_size=data['max_position_size'],
            recommendations=data.get('recommendations', []),
            assessed_at=datetime.fromisoformat(data['assessed_at'])
        )


@dataclass
class ExecutionResult:
    """
    Order execution result data model.
    """
    order_id: str
    opportunity_id: str
    status: str
    fill_price: Optional[float] = None
    fill_quantity: float = 0.0
    fees: float = 0.0
    executed_at: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'order_id': self.order_id,
            'opportunity_id': self.opportunity_id,
            'status': self.status,
            'fill_price': self.fill_price,
            'fill_quantity': self.fill_quantity,
            'fees': self.fees,
            'executed_at': self.executed_at.isoformat(),
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ExecutionResult':
        """Create from dictionary."""
        return cls(
            order_id=data['order_id'],
            opportunity_id=data['opportunity_id'],
            status=data['status'],
            fill_price=data.get('fill_price'),
            fill_quantity=data.get('fill_quantity', 0.0),
            fees=data.get('fees', 0.0),
            executed_at=datetime.fromisoformat(data['executed_at']),
            error_message=data.get('error_message')
        )
