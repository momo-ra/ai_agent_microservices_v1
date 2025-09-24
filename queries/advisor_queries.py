from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from utils.log import setup_logger
from typing import Dict, Any, Optional

logger = setup_logger(__name__)

async def get_advisor_data(session: AsyncSession, tag_id: str, target_value: float, unit_of_measure: str) -> Optional[Dict[str, Any]]:
    """
    Query function to get advisor data based on tag_id, target_value, and unit_of_measure.
    This function will be called by the advisor service to prepare data for the external function.
    
    Args:
        session: Database session
        tag_id: ID of the tag to analyze
        target_value: Target value for the tag
        unit_of_measure: Unit of measure for the target value
    
    Returns:
        Dictionary containing the data needed for the advisor service
    """
    try:
        logger.info(f'Getting advisor data for tag_id: {tag_id}, target_value: {target_value}, unit: {unit_of_measure}')
        
        # Query to get tag information and related data
        # This is a placeholder query - you may need to adjust based on your actual database schema
        query = text("""
            SELECT 
                t.tag_id,
                t.tag_name,
                t.unit_of_measure,
                t.data_type,
                t.description,
                p.plant_id,
                p.plant_name,
                p.plant_type
            FROM tags t
            LEFT JOIN plants p ON t.plant_id = p.plant_id
            WHERE t.tag_id = :tag_id
        """)
        
        result = await session.execute(query, {"tag_id": tag_id})
        tag_data = result.fetchone()
        
        if not tag_data:
            logger.warning(f'No tag found with ID: {tag_id}')
            return None
        
        # Prepare the data structure for the advisor service
        advisor_data = {
            "tag_id": tag_data.tag_id,
            "tag_name": tag_data.tag_name,
            "current_unit": tag_data.unit_of_measure,
            "target_value": target_value,
            "target_unit": unit_of_measure,
            "data_type": tag_data.data_type,
            "description": tag_data.description,
            "plant_id": tag_data.plant_id,
            "plant_name": tag_data.plant_name,
            "plant_type": tag_data.plant_type
        }
        
        logger.success(f'Retrieved advisor data for tag: {tag_id}')
        return advisor_data
        
    except Exception as e:
        logger.error(f'Error getting advisor data: {e}')
        raise e

async def get_related_tags(session: AsyncSession, plant_id: str, tag_id: str) -> Optional[list]:
    """
    Get related tags for the same plant to provide context for the advisor service.
    
    Args:
        session: Database session
        plant_id: ID of the plant
        tag_id: ID of the current tag (to exclude from results)
    
    Returns:
        List of related tag information
    """
    try:
        logger.info(f'Getting related tags for plant: {plant_id}, excluding tag: {tag_id}')
        
        query = text("""
            SELECT 
                tag_id,
                tag_name,
                unit_of_measure,
                data_type,
                description
            FROM tags
            WHERE plant_id = :plant_id 
            AND tag_id != :tag_id
            ORDER BY tag_name
        """)
        
        result = await session.execute(query, {"plant_id": plant_id, "tag_id": tag_id})
        related_tags = result.fetchall()
        
        related_tags_list = []
        for tag in related_tags:
            related_tags_list.append({
                "tag_id": tag.tag_id,
                "tag_name": tag.tag_name,
                "unit_of_measure": tag.unit_of_measure,
                "data_type": tag.data_type,
                "description": tag.description
            })
        
        logger.info(f'Found {len(related_tags_list)} related tags')
        return related_tags_list
        
    except Exception as e:
        logger.error(f'Error getting related tags: {e}')
        raise e
