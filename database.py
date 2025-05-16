from core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from utils.log import setup_logger

logger = setup_logger(__name__)

if 'DATABASE_URL' in settings.CONFIG():
    DATABASE_URL = settings.CONFIG()['DATABASE_URL']
else:
    raise ValueError('Database environment variables not set')

async_engin = create_async_engine(DATABASE_URL, future = True)

AsyncSessionLocal = sessionmaker(
    bind = async_engin,
    class_ = AsyncSession,
    expire_on_commit = False
)

Base = declarative_base()

async def init_db():
    try:
        async with async_engin.connect() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.success('Database tables created successfully')
    except Exception as e:
        logger.error(f'Error creating database tables: {e}')
        raise e
    