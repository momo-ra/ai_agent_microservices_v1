from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.endpoints import router
from routers.query_endpoint import query_router
from database import init_db
from utils.log import setup_logger
from utils.response import success_response

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
        logger.info("Starting up the application...")
        # Initialize central and plant databases
        await init_db()
        logger.success("Databases initialized")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise e
    
@app.get("/")
async def root():
    return success_response(message="Welcome in AI-Agent Microservices")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)