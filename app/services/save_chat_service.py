from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.db.models import ChatSession
from app.models.chat import ChatMessageWithMetadata, SaveChatResponse

logger = logging.getLogger(__name__)


class SaveChatService:
    """Service for persisting chat session snapshots."""

    def __init__(self, db: Session):
        self._db = db

    def save_session(
        self,
        mode: str,
        history: list[ChatMessageWithMetadata],
        version: float | None = None,
        helpful: bool = False,
    ) -> SaveChatResponse:
        """
        Save a complete chat session snapshot to the database.
        
        Args:
            mode: Chat mode (basic/rag/mcp/agent)
            history: List of messages with metadata
            version: Optional version identifier
            helpful: Whether the conversation was helpful
            
        Returns:
            SaveChatResponse with session details
        """
        try:
            # Convert Pydantic models to dict for JSONB storage
            history_data = [msg.model_dump() for msg in history]
            
            # Create new chat session record
            chat_session = ChatSession(
                mode=mode,
                history=history_data,
                version=version,
                helpful=helpful,
            )
            
            self._db.add(chat_session)
            self._db.commit()
            self._db.refresh(chat_session)
            
            logger.info(
                f"Saved chat session {chat_session.id} "
                f"(mode={mode}, messages={len(history)}, version={version})"
            )
            
            return SaveChatResponse(
                id=chat_session.id,
                created_at=chat_session.created_at,
                mode=chat_session.mode,
                version=chat_session.version,
                helpful=chat_session.helpful,
            )
            
        except Exception as e:
            self._db.rollback()
            logger.exception(f"Failed to save chat session: {e}")
            raise

    def get_session(self, session_id: int) -> ChatSession | None:
        """
        Retrieve a chat session by ID.
        
        Args:
            session_id: The session ID to retrieve
            
        Returns:
            ChatSession instance or None if not found
        """
        return (
            self._db.query(ChatSession)
            .filter(ChatSession.id == session_id)
            .first()
        )

    def list_sessions(
        self,
        mode: str | None = None,
        version: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatSession]:
        """
        List chat sessions with optional filtering.
        
        Args:
            mode: Filter by mode
            version: Filter by version
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of ChatSession instances
        """
        query = self._db.query(ChatSession).order_by(
            ChatSession.created_at.desc()
        )
        
        if mode:
            query = query.filter(ChatSession.mode == mode)
        if version is not None:
            query = query.filter(ChatSession.version == version)
            
        return query.limit(limit).offset(offset).all()
