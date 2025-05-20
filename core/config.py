from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv('.env', override=True)

class Settings:
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_NAME = os.getenv('DB_NAME')
    DB_DRIVER = os.getenv('SSL_MODE', 'require')

    @property
    def DATABASE_URL(self):
        if not all([self.DB_USER, self.DB_PASSWORD, self.DB_HOST, self.DB_PORT, self.DB_NAME]):
            raise ValueError('Database environment variables not set')
        if self.DB_DRIVER == 'require':
            return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'
        return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?sslmode={self.DB_DRIVER}'
    
    def CONFIG(self):
        required_field = ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_NAME']
        if not all(getattr(self, field) for field in required_field):
            raise ValueError('Missing required environment variables')
        return {
            'user': self.DB_USER,
            'password': self.DB_PASSWORD,
            'host': self.DB_HOST,
            'port': self.DB_PORT,
            'database': self.DB_NAME,
            'DATABASE_URL': self.DATABASE_URL
        }

settings = Settings()