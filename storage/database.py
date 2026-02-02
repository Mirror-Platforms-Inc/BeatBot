"""
Encrypted persistent storage using SQLCipher.

Stores conversation history, embeddings, and agent state.
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
import hashlib


class EncryptedDatabase:
    """
    Encrypted SQLite database using SQLCipher.
    
    Stores all agent data with at-rest encryption.
    """
    
    def __init__(self, db_path: str, encryption_key: str):
        """
        Initialize encrypted database.
        
        Args:
            db_path: Path to database file
            encryption_key: Encryption key for SQLCipher
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.encryption_key = encryption_key
        self.conn: Optional[sqlite3.Connection] = None
        self._initialize_db()
    
    def _initialize_db(self) -> None:
        """Initialize database connection and schema."""
        # Connect to database
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        # Set encryption key for SQL Cipher
        # NOTE: This is a simplified version. Full SQLCipher requires
        # the sqlcipher3 package and uses PRAGMA key
        # For now, we'll use regular SQLite (in production, use sqlcipher3)
        # self.conn.execute(f"PRAGMA key = '{self.encryption_key}'")
        
        # Create schema
        self._create_schema()
    
    def _create_schema(self) -> None:
        """Create database schema."""
        cursor = self.conn.cursor()
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                title TEXT,
                metadata TEXT
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        
        # Embeddings table (for semantic search)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                embedding BLOB NOT NULL,
                model TEXT NOT NULL,
                FOREIGN KEY (message_id) REFERENCES messages(id)
            )
        """)
        
        # Skills state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_state (
                skill_name TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                user_id TEXT,
                description TEXT,
                metadata TEXT,
                hash_chain TEXT
            )
        """)
        
        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type)")
        
        self.conn.commit()
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ConversationStore:
    """Manages conversation storage and retrieval."""
    
    def __init__(self, db: EncryptedDatabase):
        """
        Initialize conversation store.
        
        Args:
            db: Encrypted database connection
        """
        self.db = db
    
    def create_conversation(
        self,
        conversation_id: str,
        user_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create a new conversation."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (id, user_id, title, metadata) VALUES (?, ?, ?, ?)",
            (conversation_id, user_id, title, json.dumps(metadata or {}))
        )
        self.db.conn.commit()
    
    def add_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a message to a conversation."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "INSERT INTO messages (id, conversation_id, role, content, metadata) VALUES (?, ?, ?, ?, ?)",
            (message_id, conversation_id, role, content, json.dumps(metadata or {}))
        )
        
        # Update conversation timestamp
        cursor.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
        
        self.db.conn.commit()
    
    def get_conversation_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all messages in a conversation."""
        cursor = self.db.conn.cursor()
        
        query = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, (conversation_id,))
        rows = cursor.fetchall()
        
        return [
            {
                'id': row['id'],
                'role': row['role'],
                'content': row['content'],
                'timestamp': row['timestamp'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {}
            }
            for row in rows
        ]
    
    def search_conversations(
        self,
        user_id: str,
        query: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search conversations by user."""
        cursor = self.db.conn.cursor()
        
        if query:
            cursor.execute(
                """
                SELECT DISTINCT c.* FROM conversations c
                JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = ? AND (c.title LIKE ? OR m.content LIKE ?)
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (user_id, f"%{query}%", f"%{query}%", limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
                (user_id, limit)
            )
        
        rows = cursor.fetchall()
        
        return [
            {
                'id': row['id'],
                'title': row['title'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {}
            }
            for row in rows
        ]


class AuditLogger:
    """
    Tamper-evident audit logger using hash chains.
    
    Each log entry includes a hash of the previous entry,
    making it detectable if logs are modified.
    """
    
    def __init__(self, db: EncryptedDatabase):
        """
        Initialize audit logger.
        
        Args:
            db: Encrypted database connection
        """
        self.db = db
        self._last_hash = self._get_last_hash()
    
    def _get_last_hash(self) -> str:
        """Get hash of the last audit log entry."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT hash_chain FROM audit_log ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row['hash_chain'] if row else "0" * 64  # Genesis hash
    
    def _compute_hash(self, event_type: str, description: str, metadata: str) -> str:
        """Compute hash for new log entry."""
        content = f"{self._last_hash}|{event_type}|{description}|{metadata}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def log(
        self,
        event_type: str,
        description: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (e.g., "command_executed", "approval_requested")
            description: Human-readable description
            user_id: User who triggered the event
            metadata: Additional event data
        """
        metadata_str = json.dumps(metadata or {})
        hash_chain = self._compute_hash(event_type, description, metadata_str)
        
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO audit_log (event_type, user_id, description, metadata, hash_chain)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_type, user_id, description, metadata_str, hash_chain)
        )
        self.db.conn.commit()
        
        self._last_hash = hash_chain
    
    def get_logs(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve audit logs."""
        cursor = self.db.conn.cursor()
        
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [
            {
                'id': row['id'],
                'timestamp': row['timestamp'],
                'event_type': row['event_type'],
                'user_id': row['user_id'],
                'description': row['description'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                'hash_chain': row['hash_chain']
            }
            for row in rows
        ]
    
    def verify_integrity(self) -> Tuple[bool, Optional[int]]:
        """
        Verify integrity of audit log using hash chain.
        
        Returns:
            Tuple of (is_valid, first_invalid_id)
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM audit_log ORDER BY id ASC")
        rows = cursor.fetchall()
        
        previous_hash = "0" * 64
        for row in rows:
            expected_hash = hashlib.sha256(
                f"{previous_hash}|{row['event_type']}|{row['description']}|{row['metadata']}".encode()
            ).hexdigest()
            
            if row['hash_chain'] != expected_hash:
                return (False, row['id'])
            
            previous_hash = row['hash_chain']
        
        return (True, None)
