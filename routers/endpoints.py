# api/endpoints.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, List, Any
from services.ai_agent_service import ChatService
from schemas.schema import ResponseModel, MessageRequest
from middlewares.auth_middleware import authenticate_user
from utils.response import success_response, fail_response
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_plant_db_with_context

router = APIRouter(tags=["chat"])

# Dependency to get chat service
def get_chat_service():
    return ChatService()

@router.post("/session", status_code=status.HTTP_201_CREATED, response_model=ResponseModel)
async def create_chat_session(
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Create a new chat session"""
    try:
        session_id = await chat_service.create_session(db=db, user_id=auth_data.get("user_id"))
        return success_response(data={"session_id": session_id}, message="Session created", status_code=201)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.get("/session/{session_id}/history", response_model=ResponseModel)
async def get_chat_history(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Get the chat history for a session"""
    try:
        history = await chat_service.get_session_history(db=db, session_id=session_id, auth_data=auth_data)
        return success_response(data=history, message="History fetched successfully")
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.post("/session/{session_id}/message", response_model=ResponseModel)
async def send_message(
    session_id: str, 
    request: MessageRequest,
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Send a message to the chat session and get a response"""
    try:
        response = await chat_service.send_message(
            db=db,
            session_id=session_id,
            message=request.message,
            auth_data=auth_data
        )
        return success_response(data=response, message="Message sent successfully")
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.get("/session/{session_id}", response_model=ResponseModel)
async def get_session_info(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Get information about a chat session"""
    try:
        info = await chat_service.get_session_info(db=db, session_id=session_id, auth_data=auth_data)
        return success_response(data=info, message="Session info fetched successfully")
    except ValueError as e:
        return fail_response(message=str(e), status_code=404)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)
    
@router.get("/diagnostics/ai-connection", response_model=ResponseModel)
async def diagnose_ai_connection(url: Any = None):
    """Diagnose connection to AI service"""
    from utils.check_ai_connection import test_ai_connection
    result = await test_ai_connection(url)
    if result:
        return success_response(message="Successfully connected to AI service")
    else:
        return fail_response(message="Failed to connect to AI service. Check logs for details.", status_code=500)