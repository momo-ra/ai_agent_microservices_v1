from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from models.plant_models import Artifacts, ChatSession
from typing import List, Optional, Dict, Any
from utils.log import setup_logger

logger = setup_logger(__name__)

async def create_artifact(
    db: AsyncSession,
    session_id: str,
    user_id: int,
    title: str,
    content: str,
    artifact_type: str = "general",
    artifact_metadata: Optional[Dict[str, Any]] = None,
    message_id: Optional[int] = None
) -> Optional[Artifacts]:
    """Create a new artifact"""
    try:
        artifact = Artifacts(
            session_id=session_id,
            user_id=user_id,
            title=title,
            content=content,
            artifact_type=artifact_type,
            artifact_metadata=artifact_metadata,
            message_id=message_id
        )
        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)
        logger.success(f"Created artifact {artifact.id} for session {session_id}")
        return artifact
    except Exception as e:
        logger.error(f"Error creating artifact: {e}")
        await db.rollback()
        return None

async def get_artifact_by_id(
    db: AsyncSession,
    artifact_id: int,
    user_id: int
) -> Optional[Artifacts]:
    """Get an artifact by ID"""
    try:
        query = select(Artifacts).where(
            Artifacts.id == artifact_id,
            Artifacts.user_id == user_id,
            Artifacts.is_active == True
        )
        result = await db.execute(query)
        artifact = result.scalar_one_or_none()
        return artifact
    except Exception as e:
        logger.error(f"Error getting artifact {artifact_id}: {e}")
        return None

async def get_artifacts_by_session(
    db: AsyncSession,
    session_id: str,
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Artifacts]:
    """Get all artifacts for a session"""
    try:
        query = select(Artifacts).where(
            Artifacts.session_id == session_id,
            Artifacts.user_id == user_id,
            Artifacts.is_active == True
        ).order_by(Artifacts.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        artifacts = result.scalars().all()
        logger.info(f"Retrieved {len(artifacts)} artifacts for session {session_id}")
        return list(artifacts)
    except Exception as e:
        logger.error(f"Error getting artifacts for session {session_id}: {e}")
        return []

async def get_artifacts_count_by_session(
    db: AsyncSession,
    session_id: str,
    user_id: int
) -> int:
    """Get count of artifacts for a session"""
    try:
        query = select(func.count(Artifacts.id)).where(
            Artifacts.session_id == session_id,
            Artifacts.user_id == user_id,
            Artifacts.is_active == True
        )
        result = await db.execute(query)
        count = result.scalar()
        return count or 0
    except Exception as e:
        logger.error(f"Error getting artifacts count for session {session_id}: {e}")
        return 0

async def update_artifact(
    db: AsyncSession,
    artifact_id: int,
    user_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    artifact_metadata: Optional[Dict[str, Any]] = None,
    is_active: Optional[bool] = None,
    message_id: Optional[int] = None
) -> Optional[Artifacts]:
    """Update an artifact"""
    try:
        # Build update data
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if content is not None:
            update_data["content"] = content
        if artifact_metadata is not None:
            update_data["artifact_metadata"] = artifact_metadata
        if is_active is not None:
            update_data["is_active"] = is_active
        if message_id is not None:
            update_data["message_id"] = message_id
        
        if not update_data:
            logger.warning("No update data provided")
            return None
        
        query = update(Artifacts).where(
            Artifacts.id == artifact_id,
            Artifacts.user_id == user_id
        ).values(**update_data)
        
        await db.execute(query)
        await db.commit()
        
        # Get updated artifact
        updated_artifact = await get_artifact_by_id(db, artifact_id, user_id)
        if updated_artifact:
            logger.success(f"Updated artifact {artifact_id}")
        return updated_artifact
    except Exception as e:
        logger.error(f"Error updating artifact {artifact_id}: {e}")
        await db.rollback()
        return None

async def delete_artifact(
    db: AsyncSession,
    artifact_id: int,
    user_id: int
) -> bool:
    """Soft delete an artifact"""
    try:
        query = update(Artifacts).where(
            Artifacts.id == artifact_id,
            Artifacts.user_id == user_id
        ).values(is_active=False)
        
        result = await db.execute(query)
        await db.commit()
        
        if result.rowcount > 0:
            logger.success(f"Deleted artifact {artifact_id}")
            return True
        else:
            logger.warning(f"Artifact {artifact_id} not found or already deleted")
            return False
    except Exception as e:
        logger.error(f"Error deleting artifact {artifact_id}: {e}")
        await db.rollback()
        return False

async def get_artifacts_by_type(
    db: AsyncSession,
    session_id: str,
    user_id: int,
    artifact_type: str,
    skip: int = 0,
    limit: int = 100
) -> List[Artifacts]:
    """Get artifacts by type for a session"""
    try:
        query = select(Artifacts).where(
            Artifacts.session_id == session_id,
            Artifacts.user_id == user_id,
            Artifacts.artifact_type == artifact_type,
            Artifacts.is_active == True
        ).order_by(Artifacts.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        artifacts = result.scalars().all()
        logger.info(f"Retrieved {len(artifacts)} {artifact_type} artifacts for session {session_id}")
        return list(artifacts)
    except Exception as e:
        logger.error(f"Error getting {artifact_type} artifacts for session {session_id}: {e}")
        return []

async def get_all_user_artifacts(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Artifacts]:
    """Get all artifacts for a user across all sessions"""
    try:
        query = select(Artifacts).where(
            Artifacts.user_id == user_id,
            Artifacts.is_active == True
        ).order_by(Artifacts.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        artifacts = result.scalars().all()
        logger.info(f"Retrieved {len(artifacts)} artifacts for user {user_id}")
        return list(artifacts)
    except Exception as e:
        logger.error(f"Error getting all artifacts for user {user_id}: {e}")
        return []

async def get_user_artifacts_count(
    db: AsyncSession,
    user_id: int
) -> int:
    """Get count of all artifacts for a user"""
    try:
        query = select(func.count(Artifacts.id)).where(
            Artifacts.user_id == user_id,
            Artifacts.is_active == True
        )
        result = await db.execute(query)
        count = result.scalar()
        return count or 0
    except Exception as e:
        logger.error(f"Error getting artifacts count for user {user_id}: {e}")
        return 0

async def get_user_artifacts_by_type(
    db: AsyncSession,
    user_id: int,
    artifact_type: str,
    skip: int = 0,
    limit: int = 100
) -> List[Artifacts]:
    """Get user artifacts by type across all sessions"""
    try:
        query = select(Artifacts).where(
            Artifacts.user_id == user_id,
            Artifacts.artifact_type == artifact_type,
            Artifacts.is_active == True
        ).order_by(Artifacts.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        artifacts = result.scalars().all()
        logger.info(f"Retrieved {len(artifacts)} {artifact_type} artifacts for user {user_id}")
        return list(artifacts)
    except Exception as e:
        logger.error(f"Error getting {artifact_type} artifacts for user {user_id}: {e}")
        return []

async def search_user_artifacts(
    db: AsyncSession,
    user_id: int,
    search_term: str,
    skip: int = 0,
    limit: int = 100
) -> List[Artifacts]:
    """Search user artifacts across all sessions"""
    try:
        query = select(Artifacts).where(
            Artifacts.user_id == user_id,
            Artifacts.is_active == True,
            (Artifacts.title.ilike(f"%{search_term}%") | 
             Artifacts.content.ilike(f"%{search_term}%"))
        ).order_by(Artifacts.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        artifacts = result.scalars().all()
        logger.info(f"Found {len(artifacts)} artifacts matching '{search_term}' for user {user_id}")
        return list(artifacts)
    except Exception as e:
        logger.error(f"Error searching artifacts for user {user_id}: {e}")
        return []

async def search_artifacts(
    db: AsyncSession,
    session_id: str,
    user_id: int,
    search_term: str,
    skip: int = 0,
    limit: int = 100
) -> List[Artifacts]:
    """Search artifacts by title or content"""
    try:
        query = select(Artifacts).where(
            Artifacts.session_id == session_id,
            Artifacts.user_id == user_id,
            Artifacts.is_active == True,
            (Artifacts.title.ilike(f"%{search_term}%") | 
             Artifacts.content.ilike(f"%{search_term}%"))
        ).order_by(Artifacts.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        artifacts = result.scalars().all()
        logger.info(f"Found {len(artifacts)} artifacts matching '{search_term}' in session {session_id}")
        return list(artifacts)
    except Exception as e:
        logger.error(f"Error searching artifacts in session {session_id}: {e}")
        return []
