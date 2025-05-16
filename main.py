from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.endpoints import router
from api.query_endpoint import query_router
from database import async_engin, Base
from models.models import ChatSession, ChatMessage  # استيراد النماذج هنا مهم!
from utils.log import setup_logger

logger = setup_logger(__name__)

app = FastAPI()

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(router, prefix="/api/v1")
app.include_router(query_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    try:
        async with async_engin.begin() as conn:  # استخدم begin() بدلاً من connect()
            await conn.run_sync(Base.metadata.create_all)
        logger.success('Database tables created successfully')
    except Exception as e:
        logger.error(f'Error creating database tables: {e}')
        raise e
    
@app.get("/")
async def root():
    return {"message": "Welcome in AI-Agent Microservices"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)