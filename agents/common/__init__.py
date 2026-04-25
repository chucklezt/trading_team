"""Common utilities and base classes for trading agents."""

from .models import Opportunity, Position, Order

# Setup logging
import logging

def setup_logging(name: str):
    """Setup logging for a module."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(name)

# MessageQueue and Database require optional dependencies
# Import them here when available
try:
    from .message_queue import MessageQueue
except ImportError:
    MessageQueue = None

try:
    from .database import Database
except ImportError:
    Database = None

__all__ = [
    'MessageQueue',
    'Database',
    'Opportunity',
    'Position',
    'Order',
    'setup_logging'
]
