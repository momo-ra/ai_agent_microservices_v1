from typing import AsyncGenerator, Any
from neo4j import AsyncSession

class DatabaseInterface:
    """Interface for database operations"""
    async def get_session(self) -> AsyncGenerator[AsyncSession, Any]:
        """Get a database session"""
        raise NotImplementedError

    async def close(self):
        """Close database connections"""
        raise NotImplementedError 