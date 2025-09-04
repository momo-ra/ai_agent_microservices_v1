from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from models.plant_models import ChatSession
from utils.log import setup_logger
import datetime

logger = setup_logger(__name__)

async def create_chat_session(db: AsyncSession, session_id: str, user_id: int):
    try:
        async with db.begin():
            chat_session = ChatSession(session_id=session_id, user_id=user_id)
            db.add(chat_session)
            await db.commit()
            logger.info(f'Chat session created with session_id: {session_id}')
            return session_id
    except Exception as e:
        logger.error(f'Error creating chat session: {e}')
        raise  # Raise the exception after logging

async def get_chat_session(db: AsyncSession, session_id: str):
    try:
        query = select(ChatSession).where(ChatSession.session_id == session_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f'Error getting chat session: {e}')
        raise  # Raise the exception after logging
    
async def update_chat_session(db: AsyncSession, session_id: str):
    try:
        query = update(ChatSession).where(ChatSession.session_id == session_id).values(updated_at=datetime.datetime.utcnow())
        await db.execute(query)
        await db.commit()  # Ensure the changes are committed
        logger.info(f'Chat session updated for session_id: {session_id}')
    except Exception as e:
        logger.error(f'Error updating chat session: {e}')
        raise  # Raise the exception after logging

# get the whole session using user id
async def get_user_sessions(db: AsyncSession, user_id: int):
    try:
        query = select(ChatSession).where(ChatSession.user_id == user_id)
        result = await db.execute(query)
        sessions = result.scalars().all()
        logger.info(f'Retrieved {len(sessions)} sessions for user: {user_id}')
        return sessions
    except Exception as e:
        logger.error(f'Error getting user sessions: {e}')
        raise  # Raise the exception after logging 