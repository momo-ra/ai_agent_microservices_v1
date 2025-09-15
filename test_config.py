#!/usr/bin/env python3
"""
Test script to verify the multi-database configuration
"""

import asyncio
import sys
from core.config import settings
from database import init_db, check_db_health, get_active_plants
from utils.log import setup_logger

logger = setup_logger(__name__)

async def test_configuration():
    """Test the multi-database configuration"""
    try:
        logger.info("Testing multi-database configuration...")
        
        # Test central database configuration
        logger.info("Testing central database configuration...")
        central_url = settings.CENTRAL_DATABASE_URL
        logger.success(f"Central database URL: {central_url}")
        
        # Test plant database configuration (if available)
        logger.info("Testing plant database configuration...")
        try:
            # Try to get a plant database URL (this will fail if no plants are configured)
            test_plant_key = "TEST_PLANT"
            plant_url = settings.get_plant_database_url(test_plant_key)
            logger.success(f"Test plant database URL: {plant_url}")
        except ValueError as e:
            logger.warning(f"Plant database test failed (expected): {e}")
        
        # Test database initialization
        logger.info("Testing database initialization...")
        try:
            await init_db()
            logger.success("Database initialization completed")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
        
        # Test health check
        logger.info("Testing health check...")
        try:
            health_status = await check_db_health()
            logger.success(f"Health check completed: {health_status}")
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
        
        # Test active plants
        logger.info("Testing active plants...")
        try:
            plants = await get_active_plants()
            logger.success(f"Active plants: {plants}")
        except Exception as e:
            logger.error(f"Active plants test failed: {e}")
            return False
        
        logger.success("All configuration tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Configuration test failed: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("Starting configuration test...")
    
    success = await test_configuration()
    
    if success:
        logger.success("Configuration test completed successfully!")
        sys.exit(0)
    else:
        logger.error("Configuration test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
