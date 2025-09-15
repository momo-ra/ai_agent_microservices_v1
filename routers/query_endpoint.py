# api/query_endpoints.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
from services.query_service import QueryService
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_plant_db_with_context, get_plant_context
from middlewares.plant_access_middleware import validate_plant_access_middleware

query_router = APIRouter(prefix="/query", tags=["query"])

# Request and response models
class QueryTransformRequest(BaseModel):
    query: str
    original_column_names: Optional[Dict[str, str]] = None  # Map original columns to desired names

class QueryTransformResponse(BaseModel):
    original_query: str
    transformed_query: str

class QueryExecuteRequest(BaseModel):
    query: str
    parameters: Optional[Dict[str, Any]] = None

class QueryExecuteResponse(BaseModel):
    query: str
    results: list
    row_count: int
    execution_time_ms: float

# Dependency
async def get_query_service():
    return QueryService()

@query_router.post("/transform", response_model=QueryTransformResponse)
async def transform_query(
    request: QueryTransformRequest,
    query_service: QueryService = Depends(get_query_service)
):
    """
    Transform a query using WITH clause to standardize column names
    """
    try:
        transformed_query = await query_service.transform_query(
            request.query, 
            request.original_column_names
        )
        
        return QueryTransformResponse(
            original_query=request.query,
            transformed_query=transformed_query
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error transforming query: {str(e)}")

@query_router.post("/execute", response_model=QueryExecuteResponse)
async def execute_query(
    request: QueryExecuteRequest,
    query_service: QueryService = Depends(get_query_service),
    db: AsyncSession = Depends(get_plant_db_with_context),
    plant_context: dict = Depends(validate_plant_access_middleware)
):
    """
    Transform and execute a query, returning standardized results
    """
    try:
        # First transform the query
        transformed_query = await query_service.transform_query(request.query)
        
        # Then execute it with plant access validation
        results, row_count, execution_time = await query_service.execute_query(
            db,
            transformed_query,
            request.parameters,
            user_id=plant_context.get("auth_user_id"),
            plant_id=plant_context.get("plant_id")
        )
        
        return QueryExecuteResponse(
            query=transformed_query,
            results=results,
            row_count=row_count,
            execution_time_ms=execution_time
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error executing query: {str(e)}")

@query_router.post("/analyze", response_model=Dict[str, Any])
async def analyze_query(
    request: QueryTransformRequest,
    query_service: QueryService = Depends(get_query_service)
):
    """
    Analyze a query to extract key information
    """
    try:
        analysis = await query_service.analyze_query(request.query)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error analyzing query: {str(e)}")