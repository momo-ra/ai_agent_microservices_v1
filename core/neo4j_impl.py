from typing import AsyncGenerator, Any, Optional
from neo4j import AsyncSession
from .interface import DatabaseInterface
from database import get_plant_neo4j_db

class PlantNeo4jDatabase(DatabaseInterface):
    """Neo4j database implementation for plant-specific database"""

    def __init__(self, plant_id: str):
        self.plant_id = plant_id
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, Any]:
        """Get a plant-specific Neo4j database session"""
        async for session in get_plant_neo4j_db(self.plant_id):
            yield session

    async def close(self):
        """Close Neo4j database connections"""
        # Add any cleanup logic here if needed
        pass 