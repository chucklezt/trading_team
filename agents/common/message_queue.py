"""Redis-based message queue for agent communication."""

import asyncio
import json
import redis
from datetime import datetime
import uuid


class MessageQueue:
    """
    Redis Pub/Sub message queue for inter-agent communication.
    
    Supports:
    - Publishing messages to channels
    - Subscribing to channels
    - Message acknowledgment
    - Correlation tracking
    """
    
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True
        )
        self.subscribers = {}
    
    async def publish(self, channel: str, message: dict) -> bool:
        """
        Publish a message to a channel.
        
        Args:
            channel: Channel name
            message: Message dictionary to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            msg_data = self._serialize_message(message)
            await self.redis.publish(channel, msg_data)
            return True
        except Exception as e:
            print(f"Error publishing to {channel}: {e}")
            return False
    
    async def subscribe(self, channel: str, callback):
        """
        Subscribe to a channel and process messages.
        
        Args:
            channel: Channel name
            callback: Async function to process messages
        """
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    await callback(message['data'])
                except Exception as e:
                    print(f"Error processing message: {e}")
        
        self.subscribers[channel] = pubsub
    
    async def unsubscribe(self, channel: str):
        """Unsubscribe from a channel."""
        if channel in self.subscribers:
            pubsub = self.subscribers[channel]
            await pubsub.unsubscribe(channel)
            del self.subscribers[channel]
    
    def _serialize_message(self, message: dict) -> str:
        """
        Serialize message with timestamp and correlation ID.
        
        Args:
            message: Message dictionary
            
        Returns:
            JSON string with metadata
        """
        message['timestamp'] = datetime.utcnow().isoformat()
        message['correlation_id'] = message.get('correlation_id', str(uuid.uuid4()))
        
        return json.dumps(message)
    
    def _deserialize_message(self, data: str) -> dict:
        """
        Deserialize message from JSON string.
        
        Args:
            data: JSON string
            
        Returns:
            Message dictionary
        """
        return json.loads(data)
    
    async def send_opportunity(self, opportunity: dict) -> bool:
        """
        Send opportunity message to scanner channel.
        
        Args:
            opportunity: Opportunity dictionary
            
        Returns:
            True if successful
        """
        return await self.publish('trading:opportunities', opportunity)
    
    async def send_validation_result(self, opportunity_id: str, result: dict) -> bool:
        """
        Send validation result to risk manager.
        
        Args:
            opportunity_id: Opportunity ID
            result: Validation result dictionary
            
        Returns:
            True if successful
        """
        message = {
            'type': 'validation_result',
            'opportunity_id': opportunity_id,
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        return await self.publish('trading:risk', message)
    
    async def send_risk_assessment(self, opportunity_id: str, assessment: dict) -> bool:
        """
        Send risk assessment to executor.
        
        Args:
            opportunity_id: Opportunity ID
            assessment: Risk assessment dictionary
            
        Returns:
            True if successful
        """
        message = {
            'type': 'risk_assessment',
            'opportunity_id': opportunity_id,
            'assessment': assessment,
            'timestamp': datetime.utcnow().isoformat()
        }
        return await self.publish('trading:execution', message)
    
    async def send_execution_result(self, order_id: str, result: dict) -> bool:
        """
        Send execution result to reconciler.
        
        Args:
            order_id: Order ID
            result: Execution result dictionary
            
        Returns:
            True if successful
        """
        message = {
            'type': 'execution_result',
            'order_id': order_id,
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        return await self.publish('trading:reconciliation', message)
    
    async def broadcast_alert(self, alert_type: str, message: str, severity: str = 'info') -> bool:
        """
        Broadcast alert to all agents.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Severity level (info, warning, error, critical)
            
        Returns:
            True if successful
        """
        for channel in ['trading:opportunities', 'trading:risk', 'trading:execution', 'trading:reconciliation']:
            await self.publish(channel, {
                'type': 'alert',
                'alert_type': alert_type,
                'message': message,
                'severity': severity,
                'timestamp': datetime.utcnow().isoformat()
            })
