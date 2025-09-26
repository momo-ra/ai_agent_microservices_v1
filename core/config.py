import os
from dotenv import load_dotenv
from utils.log import setup_logger

logger = setup_logger(__name__)

# Load environment variables from .env file
load_dotenv('.env', override=True)

class Settings:
    # Central database settings
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME")
    
    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    
    # JWT settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your_secret_key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    
    # Central Neo4j settings (for system-wide operations) - Optional
    # Note: This is not used in the current architecture
    # Each plant has its own Neo4j database configured in plants_registry
    NEO4J_HOST: str = os.getenv("NEO4J_HOST", "")
    NEO4J_PORT: str = os.getenv("NEO4J_PORT", "")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")

    @property
    def CENTRAL_DATABASE_URL(self):
        if not all([self.DB_USER, self.DB_PASSWORD, self.DB_HOST, self.DB_PORT, self.DB_NAME]):
            logger.error("Missing required environment variables for central database")
            raise ValueError("Missing required environment variables for central database")
        logger.success(f"Central database configuration loaded")
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def CENTRAL_NEO4J_CONFIGURED(self):
        """Check if central Neo4j is configured"""
        # Central Neo4j is not used in this architecture
        # Each plant has its own Neo4j database
        return False
    
    def get_plant_database_url(self, database_key: str) -> str:
        """Get database URL for a specific plant using its database key"""
        db_user = os.getenv(f"{database_key}_USER")
        db_password = os.getenv(f"{database_key}_PASSWORD")
        db_host = os.getenv(f"{database_key}_HOST")
        db_port = os.getenv(f"{database_key}_PORT", "5432")
        db_name = os.getenv(f"{database_key}_NAME")
        
        if not all([db_user, db_password, db_host, db_port, db_name]):
            logger.error(f"Missing required environment variables for plant database: {database_key}")
            raise ValueError(f"Missing required environment variables for plant database: {database_key}")
        
        logger.success(f"Plant database configuration loaded for {database_key}")
        return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    def get_plant_neo4j_config(self, neo4j_key: str) -> dict:
        print("--------------------------------")
        print(neo4j_key)
        print("--------------------------------")
        """Get Neo4j configuration for a specific plant using its neo4j key"""
        neo4j_host = os.getenv(f"{neo4j_key}_NEO4J_HOST")
        neo4j_port = os.getenv(f"{neo4j_key}_NEO4J_PORT")
        neo4j_user = os.getenv(f"{neo4j_key}_NEO4J_USER")
        neo4j_password = os.getenv(f"{neo4j_key}_NEO4J_PASSWORD")
        neo4j_database = os.getenv(f"{neo4j_key}_NEO4J_DATABASE", "neo4j")
        
        if not all([neo4j_host, neo4j_port, neo4j_user, neo4j_password]):
            logger.error(f"Missing required environment variables for plant Neo4j: {neo4j_key}")
            raise ValueError(f"Missing required environment variables for plant Neo4j: {neo4j_key}")
        
        # Construct the Neo4j URI
        neo4j_uri = f"bolt://{neo4j_host}:{neo4j_port}"
        
        logger.success(f"Plant Neo4j configuration loaded for {neo4j_key}")
        return {
            "uri": neo4j_uri,
            "host": neo4j_host,
            "port": neo4j_port,
            "user": neo4j_user,
            "password": neo4j_password,
            "database": neo4j_database
        }
    
settings = Settings()