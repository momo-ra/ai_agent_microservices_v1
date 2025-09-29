from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from core.config import settings
from utils.log import setup_logger
from models.central_models import CentralBase
from models.plant_models import PlantBase
from fastapi import Header, HTTPException, Depends
from typing import Optional, AsyncGenerator, Dict, Tuple
from sqlalchemy import text
import asyncio
from neo4j import AsyncGraphDatabase, AsyncSession as Neo4jAsyncSession
from core.config import settings as core_settings

logger = setup_logger(__name__)

# =============================================================================
# DATABASE ENGINES
# =============================================================================

# Central Database Engine - for users, plants, permissions
central_engine = create_async_engine(settings.CENTRAL_DATABASE_URL, echo=False, future=True)
logger.info(f"Central Database initialized")
CentralSessionLocal = async_sessionmaker(central_engine, class_=AsyncSession, expire_on_commit=False)

# Central Neo4j Database Driver - Not used in this architecture
# Each plant has its own Neo4j database configured in plants_registry
central_neo4j_driver = None
logger.info("Central Neo4j not used - each plant has its own Neo4j database")

# Plant Database Engines Cache - {plant_id: (engine, session_maker)}
plant_engines: Dict[str, Tuple] = {}
plant_engines_lock = asyncio.Lock()

# Plant Neo4j Drivers Cache - {plant_id: driver}
plant_neo4j_drivers: Dict[str, AsyncGraphDatabase] = {}
plant_neo4j_lock = asyncio.Lock()

async def get_plant_engine(plant_id: str) -> Tuple:
    """Get or create database engine for a specific plant"""
    async with plant_engines_lock:
        if plant_id in plant_engines:
            return plant_engines[plant_id]
        
        # Get plant database connection info from central database
        async with CentralSessionLocal() as session:
            query = text("""
                SELECT database_key, name 
                FROM plants_registry 
                WHERE id = :plant_id AND is_active = true
            """)
            # Convert plant_id to integer for database query
            result = await session.execute(query, {"plant_id": int(plant_id)})
            plant_info = result.fetchone()
            
            if not plant_info:
                raise HTTPException(status_code=404, detail=f"Plant {plant_id} not found or inactive")
            
            database_key = plant_info.database_key
            plant_name = plant_info.name
            
            # Get database URL using the settings method
            try:
                db_url = settings.get_plant_database_url(database_key)
            except ValueError as e:
                raise HTTPException(status_code=500, detail=str(e))
            
            # Create database engine and session maker
            engine = create_async_engine(db_url, echo=False, future=True)
            session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            
            # Cache the engine and session maker
            plant_engines[plant_id] = (engine, session_maker)
            logger.info(f"Created database connection for Plant {plant_id} ({plant_name})")
            
            return engine, session_maker

async def get_plant_neo4j_driver(plant_id: str) -> AsyncGraphDatabase:
    """Get or create Neo4j driver for a specific plant"""
    async with plant_neo4j_lock:
        if plant_id in plant_neo4j_drivers:
            return plant_neo4j_drivers[plant_id]
        
        # Get plant connection info from central database
        async with CentralSessionLocal() as session:
            query = text("""
                SELECT neo4j_key, name 
                FROM plants_registry 
                WHERE id = :plant_id AND is_active = true
            """)
            # Convert plant_id to integer for database query
            result = await session.execute(query, {"plant_id": int(plant_id)})
            plant_info = result.fetchone()
            
            if not plant_info:
                raise HTTPException(status_code=404, detail=f"Plant {plant_id} not found or inactive")
            
            neo4j_key = plant_info.neo4j_key
            plant_name = plant_info.name
            
            # Get Neo4j configuration using the settings method
            try:
                neo4j_config = core_settings.get_plant_neo4j_config(neo4j_key)
            except ValueError as e:
                raise HTTPException(status_code=500, detail=str(e))
            
            # Create Neo4j driver
            try:
                driver = AsyncGraphDatabase.driver(
                    neo4j_config["uri"],
                    auth=(neo4j_config["user"], neo4j_config["password"])
                )
                
                # Test the connection
                async with driver.session() as session:
                    result = await session.run("RETURN 1 as test")
                    await result.single()
                
                # Cache the driver
                plant_neo4j_drivers[plant_id] = driver
                logger.info(f"Created Neo4j connection for Plant {plant_id} ({plant_name}) at {neo4j_config['uri']}")
                
                return driver
            except Exception as e:
                logger.warning(f"Failed to connect to Neo4j for Plant {plant_id} ({plant_name}): {e}")
                raise HTTPException(status_code=503, detail=f"Neo4j service unavailable for Plant {plant_id}")

# =============================================================================
# DATABASE DEPENDENCIES
# =============================================================================

async def get_central_db() -> AsyncGenerator[AsyncSession, None]:
    """Central database dependency - for users, plants, permissions"""
    async with CentralSessionLocal() as session:
        try:
            logger.debug("Creating central database session")
            yield session
        except Exception as e:
            logger.error(f"Error in central database session: {e}")
            await session.rollback()
            raise e
        finally:
            await session.close()

async def get_central_neo4j_db() -> AsyncGenerator[Neo4jAsyncSession, None]:
    """Central Neo4j database dependency - for system-wide knowledge graph operations"""
    # Central Neo4j is not used in this architecture
    # Each plant has its own Neo4j database configured in plants_registry
    logger.warning("Central Neo4j not available - use plant-specific endpoints instead")
    raise HTTPException(
        status_code=400, 
        detail="Central Neo4j not available. Use plant-specific endpoints with Plant-Id header."
    )

async def get_plant_neo4j_db(plant_id: str) -> AsyncGenerator[Neo4jAsyncSession, None]:
    """Plant Neo4j database dependency - for plant-specific knowledge graph operations"""
    try:
        driver = await get_plant_neo4j_driver(plant_id)
        async with driver.session() as session:
            try:
                logger.debug(f"Creating plant Neo4j database session for Plant {plant_id}")
                yield session
            except Exception as e:
                logger.error(f"Error in plant Neo4j database session for Plant {plant_id}: {e}")
                raise e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create plant Neo4j database session for Plant {plant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Neo4j connection failed for Plant {plant_id}")

async def get_plant_db(plant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Plant database dependency - for plant-specific data"""
    try:
        _, session_maker = await get_plant_engine(plant_id)
        async with session_maker() as session:
            try:
                logger.debug(f"Creating plant database session for Plant {plant_id}")
                yield session
            except Exception as e:
                logger.error(f"Error in plant database session for Plant {plant_id}: {e}")
                await session.rollback()
                raise e
            finally:
                await session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create plant database session for Plant {plant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection failed for Plant {plant_id}")

async def get_plant_context(
    plant_id: Optional[str] = Header(None, alias="Plant-Id"),
    auth_user_id: Optional[str] = Header(None, alias="x-user-id")
) -> dict:
    """Get plant context from headers"""
    if not plant_id:
        raise HTTPException(status_code=400, detail="Plant ID header (Plant-Id) is required")
    
    return {
        "plant_id": plant_id,
        "auth_user_id": auth_user_id
    }

async def get_plant_db_with_context(
    context: dict = Depends(get_plant_context)
) -> AsyncGenerator[AsyncSession, None]:
    """Plant database with context validation"""
    async for session in get_plant_db(context["plant_id"]):
        yield session

async def get_plant_neo4j_db_with_context(
    context: dict = Depends(get_plant_context)
) -> AsyncGenerator[Neo4jAsyncSession, None]:
    """Plant Neo4j database with context validation"""
    async for session in get_plant_neo4j_db(context["plant_id"]):
        yield session

# =============================================================================
# BACKWARD COMPATIBILITY FUNCTIONS
# =============================================================================

async def get_db():
    """Original get_db function - requires plant context in headers for backward compatibility"""
    # Try to get plant_id from headers (this will work in FastAPI request context)
    try:
        from fastapi import Request
        # This is a fallback - ideally all endpoints should be updated to use get_plant_db_with_context
        raise HTTPException(
            status_code=400, 
            detail="This endpoint needs to be updated to use plant-specific database dependencies"
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Plant ID header (Plant-Id) is required for database access"
        )

async def get_neo4j_db():
    """Original get_neo4j_db function - now points to central Neo4j for backward compatibility"""
    logger.warning("Using deprecated get_neo4j_db(). Please update to use plant-specific Neo4j functions.")
    async for session in get_central_neo4j_db():
        yield session

# =============================================================================
# CONVENIENCE FUNCTIONS FOR SPECIFIC OPERATIONS
# =============================================================================

async def get_user_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for user operations (central database)"""
    async for session in get_central_db():
        yield session

async def get_workspace_db_for_plant(plant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for workspace operations for a specific plant"""
    async for session in get_plant_db(plant_id):
        yield session

async def get_tag_db_for_plant(plant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for tag operations for a specific plant"""
    async for session in get_plant_db(plant_id):
        yield session

async def get_card_db_for_plant(plant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for card operations for a specific plant"""
    async for session in get_plant_db(plant_id):
        yield session

async def get_hierarchy_neo4j_for_plant(plant_id: str) -> AsyncGenerator[Neo4jAsyncSession, None]:
    """Get Neo4j session for hierarchy operations for a specific plant"""
    async for session in get_plant_neo4j_db(plant_id):
        yield session

async def get_search_neo4j_for_plant(plant_id: str) -> AsyncGenerator[Neo4jAsyncSession, None]:
    """Get Neo4j session for search operations for a specific plant"""
    async for session in get_plant_neo4j_db(plant_id):
        yield session

# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

async def init_db():
    """Initialize central database, Neo4j, and all active plant databases"""
    logger.info("Initializing databases...")
    
    # Initialize central database first
    await init_central_db()
    
    # Initialize central Neo4j database
    await init_central_neo4j()
    
    # Get all active plants and initialize their databases
    try:
        async with CentralSessionLocal() as session:
            query = text("SELECT id, name FROM plants_registry WHERE is_active = true")
            result = await session.execute(query)
            plants = result.fetchall()
        
        if not plants:
            logger.warning("No active plants found in plants_registry")
            return
        
        # Initialize all plant databases
        for plant_id, plant_name in plants:
            try:
                await init_plant_db(str(plant_id))
                await init_plant_neo4j(str(plant_id))
                logger.success(f"Initialized databases for Plant {plant_id} ({plant_name})")
            except Exception as e:
                logger.error(f"Failed to initialize databases for Plant {plant_id} ({plant_name}): {e}")
                # Continue with other plants even if one fails
                continue
        
        logger.success("All databases initialized successfully")
        
    except Exception as e:
        logger.error(f"Error getting plant list for initialization: {e}")
        raise e

async def init_central_db():
    """Initialize central database"""
    try:
        async with central_engine.begin() as conn:
            await conn.run_sync(CentralBase.metadata.create_all)
            logger.success("Central database tables created")
    except Exception as e:
        logger.error(f"Error creating central database tables: {e}")
        raise e

async def init_central_neo4j():
    """Initialize central Neo4j database and test connection"""
    if central_neo4j_driver:
        try:
            async with central_neo4j_driver.session() as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
                logger.success("Central Neo4j database connection verified")
        except Exception as e:
            logger.error(f"Error connecting to central Neo4j database: {e}")
            raise e
    else:
        logger.warning("Central Neo4j not configured, skipping central Neo4j initialization.")

async def init_plant_db(plant_id: str):
    """Initialize a specific plant's database"""
    try:
        engine, _ = await get_plant_engine(plant_id)
        async with engine.begin() as conn:
            await conn.run_sync(PlantBase.metadata.create_all)
            logger.success(f"Plant {plant_id} database tables created")
    except Exception as e:
        logger.error(f"Error creating plant {plant_id} database tables: {e}")
        raise e

async def init_plant_neo4j(plant_id: str):
    """Initialize a specific plant's Neo4j database and test connection"""
    try:
        driver = await get_plant_neo4j_driver(plant_id)
        async with driver.session() as session:
            result = await session.run("RETURN 1 as test")
            await result.single()
            logger.success(f"Plant {plant_id} Neo4j database connection verified")
    except Exception as e:
        logger.warning(f"Neo4j database not available for plant {plant_id}: {e}")
        logger.info(f"Plant {plant_id} will continue without Neo4j functionality")
        # Don't raise the exception - allow the application to continue without Neo4j

# =============================================================================
# HEALTH CHECK & MONITORING
# =============================================================================

async def check_db_health() -> dict:
    """Check health of central database, Neo4j, and all active plant databases"""
    health_status = {
        "central_db": False,
        "central_neo4j_db": False,
        "plant_dbs": {},
        "plant_neo4j_dbs": {}
    }
    
    # Check central database
    try:
        async with CentralSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            health_status["central_db"] = True
            logger.debug("Central database health check passed")
    except Exception as e:
        logger.error(f"Central database health check failed: {e}")
        health_status["central_db"] = False
    
    # Check central Neo4j database
    if central_neo4j_driver:
        try:
            async with central_neo4j_driver.session() as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
                health_status["central_neo4j_db"] = True
                logger.debug("Central Neo4j database health check passed")
        except Exception as e:
            logger.error(f"Central Neo4j database health check failed: {e}")
            health_status["central_neo4j_db"] = False
    else:
        health_status["central_neo4j_db"] = False
        logger.warning("Central Neo4j not configured, cannot check central Neo4j health.")
    
    # Check all active plant databases
    try:
        async with CentralSessionLocal() as session:
            query = text("SELECT id, name FROM plants_registry WHERE is_active = true")
            result = await session.execute(query)
            plants = result.fetchall()
        
        for plant_id, plant_name in plants:
            plant_id_str = str(plant_id)
            
            # Check PostgreSQL database
            try:
                engine, _ = await get_plant_engine(plant_id_str)
                async with engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                    health_status["plant_dbs"][plant_id_str] = {
                        "status": True,
                        "name": plant_name
                    }
                    logger.debug(f"Plant {plant_id} ({plant_name}) database health check passed")
            except Exception as e:
                logger.error(f"Plant {plant_id} ({plant_name}) database health check failed: {e}")
                health_status["plant_dbs"][plant_id_str] = {
                    "status": False,
                    "name": plant_name,
                    "error": str(e)
                }
            
            # Check Neo4j database
            try:
                driver = await get_plant_neo4j_driver(plant_id_str)
                async with driver.session() as session:
                    result = await session.run("RETURN 1 as test")
                    await result.single()
                    health_status["plant_neo4j_dbs"][plant_id_str] = {
                        "status": True,
                        "name": plant_name
                    }
                    logger.debug(f"Plant {plant_id} ({plant_name}) Neo4j database health check passed")
            except Exception as e:
                logger.warning(f"Plant {plant_id} ({plant_name}) Neo4j database not available: {e}")
                health_status["plant_neo4j_dbs"][plant_id_str] = {
                    "status": False,
                    "name": plant_name,
                    "error": str(e),
                    "note": "Neo4j functionality disabled for this plant"
                }
    except Exception as e:
        logger.error(f"Error checking plant databases health: {e}")
    
    return health_status

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def get_active_plants() -> list:
    """Get list of all active plants"""
    try:
        async with CentralSessionLocal() as session:
            query = text("""
                SELECT id, name, database_key, neo4j_key 
                FROM plants_registry 
                WHERE is_active = true 
                ORDER BY name
            """)
            result = await session.execute(query)
            return [
                {
                    "id": row.id,
                    "name": row.name,
                    "database_key": row.database_key,
                    "neo4j_key": row.neo4j_key
                }
                for row in result.fetchall()
            ]
    except Exception as e:
        logger.error(f"Error getting active plants: {e}")
        return []

async def validate_plant_access(user_id: int, plant_id: str) -> bool:
    """Validate if user has access to a specific plant"""
    try:
        async with CentralSessionLocal() as session:
            query = text("""
                SELECT EXISTS(
                    SELECT 1 
                    FROM user_plant_access upa
                    JOIN plants_registry pr ON upa.plant_id = pr.id
                    WHERE upa.user_id = :user_id 
                    AND pr.id = :plant_id
                    AND upa.is_active = true
                    AND pr.is_active = true
                ) as has_access
            """)
            # Convert plant_id to integer for database query
            result = await session.execute(query, {"user_id": user_id, "plant_id": int(plant_id)})
            return bool(result.scalar())
    except Exception as e:
        logger.error(f"Error validating plant access for user {user_id}, plant {plant_id}: {e}")
        return False

async def close_connections():
    """Close all database connections"""
    logger.info("Closing database connections...")
    
    # Close central Neo4j driver
    if central_neo4j_driver:
        try:
            await central_neo4j_driver.close()
            logger.success("Central Neo4j driver closed")
        except Exception as e:
            logger.error(f"Error closing central Neo4j driver: {e}")
    
    # Close all plant Neo4j drivers
    async with plant_neo4j_lock:
        for plant_id, driver in plant_neo4j_drivers.items():
            try:
                await driver.close()
                logger.success(f"Plant Neo4j driver closed for Plant {plant_id}")
            except Exception as e:
                logger.error(f"Error closing plant Neo4j driver for Plant {plant_id}: {e}")
        plant_neo4j_drivers.clear()
    
    # Close central database engine
    try:
        await central_engine.dispose()
        logger.success("Central database engine closed")
    except Exception as e:
        logger.error(f"Error closing central database engine: {e}")
    
    # Close all plant database engines
    async with plant_engines_lock:
        for plant_id, (engine, _) in plant_engines.items():
            try:
                await engine.dispose()
                logger.success(f"Plant database engine closed for Plant {plant_id}")
            except Exception as e:
                logger.error(f"Error closing plant database engine for Plant {plant_id}: {e}")
        plant_engines.clear()
    
    logger.success("All database connections closed")

# =============================================================================
# BACKWARD COMPATIBILITY VARIABLES
# =============================================================================

# Keep these for backward compatibility with existing query files
# These point to the central engine by default - query files should be updated
# to use the new plant-specific database functions
engine = central_engine
SessionLocal = CentralSessionLocal
neo4j_driver = central_neo4j_driver  # This will be None if central Neo4j is not configured

if central_neo4j_driver is None:
    logger.warning("Central Neo4j not configured. Backward compatibility 'neo4j_driver' will be None.")
    logger.warning("Please update query files to use plant-specific database functions.")

logger.warning("Using deprecated 'engine', 'SessionLocal', and 'neo4j_driver' imports. Please update to use plant-specific database functions.")
