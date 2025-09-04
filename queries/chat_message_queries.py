from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.plant_models import ChatMessage
from utils.log import setup_logger
from typing import List, Optional, Dict, Any
import json

logger = setup_logger(__name__)

def message_serializer(message):
    """
    Serialize a ChatMessage to a standardized format
    """
    try:
        # Try to parse the response as JSON, otherwise return it as is
        response_data = json.loads(message.response) if message.response else []
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Could not parse response as JSON for message ID {message.id}")
        response_data = message.response
    
    return {
        "status": "success",
        "data": response_data,  # Now returning parsed JSON data
        "timestamp": message.created_at.isoformat() if hasattr(message.created_at, 'isoformat') else str(message.created_at)
    }

async def create_chat_message(db: AsyncSession, session_id: str, user_id: int, message: str, response: str, query: Optional[str] = None, execution_time: Optional[float] = None):
    """
    Create a new chat message in the database
    
    Args:
        session_id: The session ID
        message: User's input message
        response: The response from the AI (as a JSON string)
        query: SQL query executed (if any)
        execution_time: Time taken to execute the query
        
    Returns:
        Serialized message object
    """
    try:
        async with db.begin():
            chat_message = ChatMessage(
                session_id=session_id,
                user_id=user_id,
                message=message,
                query=query,
                execution_time=execution_time,
                response=response
            )
            db.add(chat_message)
            await db.commit()
            logger.success(f'Chat message created for session: {session_id}')
            return message_serializer(chat_message)
    except Exception as e:
        logger.error(f'Error creating chat message: {e}')
        raise e

async def get_session_messages(db: AsyncSession, session_id: str) -> List[ChatMessage]:
    try:
        query = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
        result = await db.execute(query)
        messages = result.scalars().all()
        logger.success(f'Chat messages retrieved for session: {session_id}')
        return messages
    except Exception as e:
        logger.error(f'Error getting chat messages: {e}')
        raise e

async def get_last_message(db: AsyncSession, session_id: str) -> Optional[ChatMessage]:

    try:
        query = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.desc()).limit(1)
        result = await db.execute(query)
        message = result.scalar_one_or_none()
        if message:
            logger.success(f'Last chat message retrieved for session: {session_id}')
        else:
            logger.info(f'No messages found for session: {session_id}')
        return message
    except Exception as e:
        logger.error(f'Error getting last chat message: {e}')
        raise e