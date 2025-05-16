# api/endpoints.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, List, Any
from services.ai_agent_service import ChatService
from schema import *

router = APIRouter(tags=["chat"])

# Dependency to get chat service
def get_chat_service():
    return ChatService()

@router.post("/session", status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    chat_service: ChatService = Depends(get_chat_service)
) -> Dict[str, str]:
    """Create a new chat session"""
    try:
        session_id = await chat_service.create_session()
        return {"session_id": session_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/session/{session_id}/history")
async def get_chat_history(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service)
) -> List[Dict[str, Any]]:
    """Get the chat history for a session"""
    try:
        history = await chat_service.get_session_history(session_id)
        return history
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/session/{session_id}/message")
async def send_message(
    session_id: str, 
    request: MessageRequest,
    chat_service: ChatService = Depends(get_chat_service)
) -> Dict[str, Any]:
    """Send a message to the chat session and get a response"""
    try:
        response = await chat_service.send_message(
            session_id=session_id,
            message=request.message
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/session/{session_id}")
async def get_session_info(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service)
) -> Dict[str, Any]:
    """Get information about a chat session"""
    try:
        info = await chat_service.get_session_info(session_id)
        return info
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    
@router.get("/diagnostics/ai-connection")
async def diagnose_ai_connection(url: Optional[str] = None):
    """Diagnose connection to AI service"""
    from utils.check_ai_connection import test_ai_connection
    result = await test_ai_connection(url)
    
    if result:
        return {"status": "success", "message": "Successfully connected to AI service"}
    else:
        return {"status": "error", "message": "Failed to connect to AI service. Check logs for details."}