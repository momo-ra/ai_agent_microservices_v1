from fastapi import HTTPException, Depends, Header
from typing import Optional
from database import validate_plant_access
from utils.log import setup_logger

logger = setup_logger(__name__)

async def validate_plant_access_middleware(
    plant_id: Optional[str] = Header(None, alias="Plant-Id"),
    auth_user_id: Optional[str] = Header(None, alias="x-user-id")
) -> dict:
    """
    Middleware to validate plant access for a user
    
    Args:
        plant_id: Plant ID from header
        auth_user_id: User ID from header
        
    Returns:
        dict: Context with plant_id and auth_user_id
        
    Raises:
        HTTPException: If plant_id is missing or user doesn't have access
    """
    if not plant_id:
        raise HTTPException(
            status_code=400, 
            detail="Plant ID header (Plant-Id) is required"
        )
    
    if not auth_user_id:
        raise HTTPException(
            status_code=401, 
            detail="User ID header (x-user-id) is required"
        )
    
    try:
        # Validate plant access
        has_access = await validate_plant_access(int(auth_user_id), plant_id)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"User {auth_user_id} does not have access to plant {plant_id}"
            )
        
        logger.info(f"Plant access validated for user {auth_user_id} to plant {plant_id}")
        return {
            "plant_id": plant_id,
            "auth_user_id": int(auth_user_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating plant access: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error validating plant access"
        )
