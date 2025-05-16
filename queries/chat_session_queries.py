from sqlalchemy import update, select
from models.models import ChatSession
from database import AsyncSessionLocal
from utils.log import setup_logger
import datetime

logger = setup_logger(__name__)

async def create_chat_session(session_id: str):
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                chat_session = ChatSession(session_id=session_id)
                session.add(chat_session)
                await session.commit()
                logger.info(f'Chat session created with session_id: {session_id}')
                return session_id
    except Exception as e:
        logger.error(f'Error creating chat session: {e}')
        raise  # Raise the exception after logging

async def get_chat_session(session_id: str):
    try:
        async with AsyncSessionLocal() as session:
            query = select(ChatSession).where(ChatSession.session_id == session_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f'Error getting chat session: {e}')
        raise  # Raise the exception after logging
    
async def update_chat_session(session_id: str):
    try:
        async with AsyncSessionLocal() as session:
            query = update(ChatSession).where(ChatSession.session_id == session_id).values(updated_at=datetime.datetime.utcnow())
            await session.execute(query)
            await session.commit()  # Ensure the changes are committed
            logger.info(f'Chat session updated for session_id: {session_id}')
    except Exception as e:
        logger.error(f'Error updating chat session: {e}')
        raise  # Raise the exception after logging
