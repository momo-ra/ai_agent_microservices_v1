from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from models.plant_models import ChatSession
from utils.log import setup_logger
import datetime

logger = setup_logger(__name__)

async def create_chat_session(db: AsyncSession, session_id: str, user_id: int):
    try:
        chat_session = ChatSession(session_id=session_id, user_id=user_id)
        db.add(chat_session)
        await db.commit()
        await db.refresh(chat_session)
        logger.info(f'Chat session created with session_id: {session_id}')
        return session_id
    except Exception as e:
        logger.error(f'Error creating chat session: {e}')
        await db.rollback()
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
async def get_user_sessions(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    try:
        query = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        sessions = result.scalars().all()
        logger.info(f'Retrieved {len(sessions)} sessions for user: {user_id}')
        return sessions
    except Exception as e:
        logger.error(f'Error getting user sessions: {e}')
        raise  # Raise the exception after logging

async def get_starred_sessions(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    try:
        query = select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.is_starred == True
        ).order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        sessions = result.scalars().all()
        logger.info(f'Retrieved {len(sessions)} starred sessions for user: {user_id}')
        return sessions
    except Exception as e:
        logger.error(f'Error getting starred sessions: {e}')
        raise

async def get_recent_sessions(db: AsyncSession, user_id: int, days: int = 7, skip: int = 0, limit: int = 100):
    try:
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.updated_at >= cutoff_date
        ).order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        sessions = result.scalars().all()
        logger.info(f'Retrieved {len(sessions)} recent sessions for user: {user_id}')
        return sessions
    except Exception as e:
        logger.error(f'Error getting recent sessions: {e}')
        raise

async def search_sessions(db: AsyncSession, user_id: int, search_term: str, skip: int = 0, limit: int = 100):
    try:
        query = select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.chat_name.ilike(f'%{search_term}%')
        ).order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        sessions = result.scalars().all()
        logger.info(f'Found {len(sessions)} sessions matching search term: {search_term}')
        return sessions
    except Exception as e:
        logger.error(f'Error searching sessions: {e}')
        raise

async def update_session_star(db: AsyncSession, session_id: str, is_starred: bool):
    try:
        query = update(ChatSession).where(ChatSession.session_id == session_id).values(is_starred=is_starred)
        await db.execute(query)
        await db.commit()
        logger.info(f'Session {session_id} starred status updated to: {is_starred}')
    except Exception as e:
        logger.error(f'Error updating session star status: {e}')
        raise

async def update_session_name(db: AsyncSession, session_id: str, chat_name: str):
    try:
        query = update(ChatSession).where(ChatSession.session_id == session_id).values(chat_name=chat_name)
        await db.execute(query)
        await db.commit()
        logger.info(f'Session {session_id} name updated to: {chat_name}')
    except Exception as e:
        logger.error(f'Error updating session name: {e}')
        raise

async def delete_session(db: AsyncSession, session_id: str):
    try:
        from models.plant_models import Artifacts
        from sqlalchemy import func
        
        # First get the session to ensure it exists
        session_query = select(ChatSession).where(ChatSession.session_id == session_id)
        result = await db.execute(session_query)
        session = result.scalar_one_or_none()
        
        if not session:
            logger.warning(f'Session {session_id} not found')
            return False
        
        # Count artifacts and messages before deletion for logging
        artifacts_count_query = select(func.count(Artifacts.id)).where(Artifacts.session_id == session_id)
        artifacts_result = await db.execute(artifacts_count_query)
        artifacts_count = artifacts_result.scalar() or 0
        
        messages_count_query = select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
        messages_result = await db.execute(messages_count_query)
        messages_count = messages_result.scalar() or 0
        
        # Use SQLAlchemy ORM delete which respects cascade relationships
        await db.delete(session)
        await db.commit()
        logger.info(f'Session {session_id} and all associated {messages_count} messages and {artifacts_count} artifacts deleted successfully')
        return True
    except Exception as e:
        logger.error(f'Error deleting session: {e}')
        await db.rollback()
        raise 