from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.endpoints import router
from routers.query_endpoint import query_router
from database import init_db, check_db_health, get_active_plants
from utils.log import setup_logger
from utils.response import success_response, fail_response

logger = setup_logger(__name__)

app = FastAPI(
    title="AI Agent Microservices",
    description="Multi-plant AI agent service with dynamic database management",
    version="2.0.0"
)

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
    return success_response(message="Welcome to AI-Agent Microservices v2.0")

@app.get("/health")
async def health_check():
    """Health check endpoint for the service"""
    try:
        health_status = await check_db_health()
        return success_response(
            data=health_status,
            message="Service health check completed"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return fail_response(
            message=f"Health check failed: {str(e)}",
            status_code=500
        )

@app.get("/plants")
async def get_plants():
    """Get list of active plants"""
    try:
        plants = await get_active_plants()
        return success_response(
            data=plants,
            message="Active plants retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting plants: {e}")
        return fail_response(
            message=f"Failed to retrieve plants: {str(e)}",
            status_code=500
        )

@app.get("/test")
async def test_endpoint():
    """Test endpoint without authentication"""
    return success_response(
        data={"message": "Service is running"},
        message="Test endpoint working"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)