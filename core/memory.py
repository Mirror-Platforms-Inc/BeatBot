"""
Persistent memory management for the agent.

Provides context retention across conversations.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from storage.database import EncryptedDatabase, ConversationStore
from models.interface import Message, MessageRole


class MemoryManager:
    """
    Manages agent's persistent memory.
    
    Handles conversation history, context window management,
    and long-term memory retrieval.
    """
    
    def __init__(
        self,
        db: EncryptedDatabase,
        context_window: int = 20,
        retention_days: int = 90
    ):
        """
        Initialize memory manager.
        
        Args:
            db: Encrypted database
            context_window: Number of recent messages to keep in context
            retention_days: Number of days to retain conversations
        """
        self.db = db
        self.store = ConversationStore(db)
        self.context_window = context_window
        self.retention_days = retention_days
        
        self.current_conversation_id: Optional[str] = None
        self.current_user_id: Optional[str] = None
    
    def start_conversation(
        self,
        user_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new conversation.
        
        Args:
            user_id: User identifier
            title: Optional conversation title
            metadata: Optional metadata
        
        Returns:
            Conversation ID
        """
        conversation_id = str(uuid.uuid4())
        self.store.create_conversation(conversation_id, user_id, title, metadata)
        
        self.current_conversation_id = conversation_id
        self.current_user_id = user_id
        
        return conversation_id
    
    def add_message(
        self,
        role: MessageRole,
        content: str,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a message to the current conversation.
        
        Args:
            role: Message role (system, user, assistant)
            content: Message content
            conversation_id: Optional conversation ID (uses current if not provided)
            metadata: Optional metadata
        
        Returns:
            Message ID
        """
        conv_id = conversation_id or self.current_conversation_id
        if not conv_id:
            raise ValueError("No active conversation. Call start_conversation() first.")
        
        message_id = str(uuid.uuid4())
        self.store.add_message(
            message_id,
            conv_id,
            role.value,
            content,
            metadata
        )
        
        return message_id
    
    def get_context(
        self,
        conversation_id: Optional[str] = None,
        max_messages: Optional[int] = None
    ) -> List[Message]:
        """
        Get conversation context for the model.
        
        Args:
            conversation_id: Optional conversation ID (uses current if not provided)
            max_messages: Maximum messages to retrieve (uses context_window if not provided)
        
        Returns:
            List of Message objects
        """
        conv_id = conversation_id or self.current_conversation_id
        if not conv_id:
            return []
        
        limit = max_messages or self.context_window
        messages = self.store.get_conversation_messages(conv_id, limit=limit)
        
        # Convert to Message objects
        return [
            Message(
                role=MessageRole(msg['role']),
                content=msg['content'],
                metadata=msg.get('metadata')
            )
            for msg in messages
        ]
    
    def search_history(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search conversation history.
        
        Args:
            query: Search query
            user_id: User to search for (uses current if not provided)
            limit: Maximum results
        
        Returns:
            List of matching conversations
        """
        uid = user_id or self.current_user_id
        if not uid:
            return []
        
        return self.store.search_conversations(uid, query, limit)
    
    def cleanup_old_conversations(self) -> int:
        """
        Delete conversations older than retention period.
        
        Returns:
            Number of conversations deleted
        """
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT id FROM conversations WHERE updated_at < ?",
            (cutoff_date.isoformat(),)
        )
        old_conv_ids = [row['id'] for row in cursor.fetchall()]
        
        for conv_id in old_conv_ids:
            # Delete messages
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
            # Delete embeddings
            cursor.execute(
                "DELETE FROM embeddings WHERE message_id IN (SELECT id FROM messages WHERE conversation_id = ?)",
                (conv_id,)
            )
            # Delete conversation
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        
        self.db.conn.commit()
        return len(old_conv_ids)
    
    def export_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Export a conversation to JSON format.
        
        Args:
            conversation_id: Conversation to export
        
        Returns:
            Dict with conversation data
        """
        messages = self.store.get_conversation_messages(conversation_id)
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        conv = cursor.fetchone()
        
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        return {
            'id': conv['id'],
            'user_id': conv['user_id'],
            'title': conv['title'],
            'created_at': conv['created_at'],
            'updated_at': conv['updated_at'],
            'messages': messages
        }
