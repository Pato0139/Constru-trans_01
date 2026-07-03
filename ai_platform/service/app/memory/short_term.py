import json
from datetime import timedelta
from typing import Dict, List, Optional

import redis

from app.core.config import settings
from app.core.logging import logger


class ShortTermMemory:
    """Short-term memory using Redis for session state"""

    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
        self.ttl = timedelta(hours=24)  # 24 hour TTL
        logger.info("ShortTermMemory initialized with Redis")

    def get_messages(self, session_id: str) -> List[Dict]:
        """Get recent messages for a session"""
        key = f"chat:session:{session_id}:messages"
        data = self.redis_client.get(key)
        if data:
            return json.loads(data)
        return []

    def add_message(self, session_id: str, message: Dict):
        """Add a message to the session"""
        key = f"chat:session:{session_id}:messages"
        messages = self.get_messages(session_id)
        messages.append(message)
        # Keep last 20 messages
        if len(messages) > 20:
            messages = messages[-20:]
        self.redis_client.setex(key, self.ttl, json.dumps(messages))

    def set_session_state(self, session_id: str, state: Dict):
        """Set arbitrary session state"""
        key = f"chat:session:{session_id}:state"
        self.redis_client.setex(key, self.ttl, json.dumps(state))

    def get_session_state(self, session_id: str) -> Optional[Dict]:
        """Get session state"""
        key = f"chat:session:{session_id}:state"
        data = self.redis_client.get(key)
        if data:
            return json.loads(data)
        return None

    def clear_session(self, session_id: str):
        """Clear all session data"""
        pattern = f"chat:session:{session_id}:*"
        keys = self.redis_client.keys(pattern)
        if keys:
            self.redis_client.delete(*keys)
        logger.info(f"Cleared session: {session_id}")


# Singleton instance
short_term_memory = ShortTermMemory()
