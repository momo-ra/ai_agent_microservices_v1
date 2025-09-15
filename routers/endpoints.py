# api/endpoints.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, List, Any
from services.ai_agent_service import ChatService
from services.artifact_service import ArtifactService
from schemas.schema import (
    ResponseModel, MessageRequest, ArtifactCreateSchema, ArtifactUpdateSchema,
    ChatSessionUpdateSchema, ChatMessageUpdateSchema, ChatSearchRequestSchema, RecentChatsRequestSchema
)
from middlewares.auth_middleware import authenticate_user
from middlewares.plant_access_middleware import validate_plant_access_middleware
from utils.response import success_response, fail_response
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_plant_db_with_context

router = APIRouter(tags=["chat"])

# Dependency to get chat service
def get_chat_service():
    return ChatService()

# Dependency to get artifact service
def get_artifact_service():
    return ArtifactService()

@router.post("/session", status_code=status.HTTP_201_CREATED, response_model=ResponseModel)
async def create_chat_session(
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
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
    plant_context: dict = Depends(validate_plant_access_middleware),
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
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Send a message to the chat session and get a response"""
    try:
        response = await chat_service.send_message(
            db=db,
            session_id=session_id,
            message=request.input_message,
            auth_data=auth_data,
            plant_context=plant_context
        )
        return success_response(data=response, message="Message sent successfully")
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.get("/session/{session_id}", response_model=ResponseModel)
async def get_session_info(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
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

# =============================================================================
# ARTIFACT ENDPOINTS
# =============================================================================

@router.post("/session/{session_id}/artifacts", status_code=status.HTTP_201_CREATED, response_model=ResponseModel)
async def create_artifact(
    session_id: str,
    artifact_data: ArtifactCreateSchema,
    artifact_service: ArtifactService = Depends(get_artifact_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Create a new artifact"""
    try:
        # Override session_id from URL parameter
        artifact_data.session_id = session_id
        
        artifact = await artifact_service.create_artifact(
            db=db,
            artifact_data=artifact_data,
            user_id=auth_data.get("user_id"),
            auth_data=auth_data
        )
        
        if artifact:
            return success_response(data=artifact, message="Artifact created successfully", status_code=201)
        else:
            return fail_response(message="Failed to create artifact", status_code=400)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.get("/session/{session_id}/artifacts", response_model=ResponseModel)
async def get_session_artifacts(
    session_id: str,
    skip: int = 0,
    limit: int = 100,
    artifact_service: ArtifactService = Depends(get_artifact_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Get all artifacts for a session"""
    try:
        result = await artifact_service.get_session_artifacts(
            db=db,
            session_id=session_id,
            user_id=auth_data.get("user_id"),
            auth_data=auth_data,
            skip=skip,
            limit=limit
        )
        
        if result is not None:
            return success_response(data=result, message="Artifacts retrieved successfully")
        else:
            return fail_response(message="Access denied or session not found", status_code=403)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.get("/artifacts/{artifact_id}", response_model=ResponseModel)
async def get_artifact(
    artifact_id: int,
    artifact_service: ArtifactService = Depends(get_artifact_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Get a specific artifact by ID"""
    try:
        artifact = await artifact_service.get_artifact(
            db=db,
            artifact_id=artifact_id,
            user_id=auth_data.get("user_id"),
            auth_data=auth_data
        )
        
        if artifact:
            return success_response(data=artifact, message="Artifact retrieved successfully")
        else:
            return fail_response(message="Artifact not found or access denied", status_code=404)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.put("/artifacts/{artifact_id}", response_model=ResponseModel)
async def update_artifact(
    artifact_id: int,
    update_data: ArtifactUpdateSchema,
    artifact_service: ArtifactService = Depends(get_artifact_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Update an artifact"""
    try:
        artifact = await artifact_service.update_artifact(
            db=db,
            artifact_id=artifact_id,
            user_id=auth_data.get("user_id"),
            update_data=update_data,
            auth_data=auth_data
        )
        
        if artifact:
            return success_response(data=artifact, message="Artifact updated successfully")
        else:
            return fail_response(message="Artifact not found or access denied", status_code=404)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.delete("/artifacts/{artifact_id}", response_model=ResponseModel)
async def delete_artifact(
    artifact_id: int,
    artifact_service: ArtifactService = Depends(get_artifact_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Delete an artifact"""
    try:
        success = await artifact_service.delete_artifact(
            db=db,
            artifact_id=artifact_id,
            user_id=auth_data.get("user_id"),
            auth_data=auth_data
        )
        
        if success:
            return success_response(message="Artifact deleted successfully")
        else:
            return fail_response(message="Artifact not found or access denied", status_code=404)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.get("/session/{session_id}/artifacts/search", response_model=ResponseModel)
async def search_artifacts(
    session_id: str,
    q: str,
    skip: int = 0,
    limit: int = 100,
    artifact_service: ArtifactService = Depends(get_artifact_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Search artifacts in a session"""
    try:
        artifacts = await artifact_service.search_artifacts(
            db=db,
            session_id=session_id,
            user_id=auth_data.get("user_id"),
            search_term=q,
            auth_data=auth_data,
            skip=skip,
            limit=limit
        )
        
        if artifacts is not None:
            return success_response(data={"artifacts": artifacts, "search_term": q}, message="Search completed successfully")
        else:
            return fail_response(message="Access denied or session not found", status_code=403)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

# =============================================================================
# USER ARTIFACTS ENDPOINTS (across all sessions)
# =============================================================================

@router.get("/user/artifacts", response_model=ResponseModel)
async def get_all_user_artifacts(
    skip: int = 0,
    limit: int = 100,
    artifact_service: ArtifactService = Depends(get_artifact_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Get all artifacts for the authenticated user across all sessions"""
    try:
        result = await artifact_service.get_all_user_artifacts(
            db=db,
            user_id=auth_data.get("user_id"),
            auth_data=auth_data,
            skip=skip,
            limit=limit
        )
        
        if result:
            return success_response(data=result, message="User artifacts retrieved successfully")
        else:
            return fail_response(message="Failed to retrieve user artifacts", status_code=500)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.get("/user/artifacts/type/{artifact_type}", response_model=ResponseModel)
async def get_user_artifacts_by_type(
    artifact_type: str,
    skip: int = 0,
    limit: int = 100,
    artifact_service: ArtifactService = Depends(get_artifact_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Get user artifacts by type across all sessions"""
    try:
        artifacts = await artifact_service.get_user_artifacts_by_type(
            db=db,
            user_id=auth_data.get("user_id"),
            artifact_type=artifact_type,
            auth_data=auth_data,
            skip=skip,
            limit=limit
        )
        
        if artifacts is not None:
            return success_response(data={"artifacts": artifacts, "artifact_type": artifact_type}, message="User artifacts by type retrieved successfully")
        else:
            return fail_response(message="Failed to retrieve user artifacts by type", status_code=500)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.get("/user/artifacts/search", response_model=ResponseModel)
async def search_user_artifacts(
    q: str,
    skip: int = 0,
    limit: int = 100,
    artifact_service: ArtifactService = Depends(get_artifact_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Search user artifacts across all sessions"""
    try:
        artifacts = await artifact_service.search_user_artifacts(
            db=db,
            user_id=auth_data.get("user_id"),
            search_term=q,
            auth_data=auth_data,
            skip=skip,
            limit=limit
        )
        
        if artifacts is not None:
            return success_response(data={"artifacts": artifacts, "search_term": q}, message="User artifacts search completed successfully")
        else:
            return fail_response(message="Failed to search user artifacts", status_code=500)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

# =============================================================================
# CHAT SESSION MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/user/sessions", response_model=ResponseModel)
async def get_all_user_sessions(
    skip: int = 0,
    limit: int = 100,
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Get all chat sessions for the logged-in user"""
    try:
        sessions = await chat_service.get_user_sessions(
            db=db,
            user_id=auth_data.get("user_id"),
            skip=skip,
            limit=limit
        )
        return success_response(
            data={
                "sessions": sessions,
                "total_count": len(sessions),
                "skip": skip,
                "limit": limit
            },
            message="User sessions retrieved successfully"
        )
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.get("/user/sessions/starred", response_model=ResponseModel)
async def get_starred_sessions(
    skip: int = 0,
    limit: int = 100,
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Get starred chat sessions for the logged-in user"""
    try:
        sessions = await chat_service.get_starred_sessions(
            db=db,
            user_id=auth_data.get("user_id"),
            skip=skip,
            limit=limit
        )
        return success_response(
            data={
                "sessions": sessions,
                "total_count": len(sessions),
                "skip": skip,
                "limit": limit
            },
            message="Starred sessions retrieved successfully"
        )
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.get("/user/sessions/recent", response_model=ResponseModel)
async def get_recent_sessions(
    days: int = 7,
    skip: int = 0,
    limit: int = 100,
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Get recent chat sessions for the logged-in user"""
    try:
        sessions = await chat_service.get_recent_sessions(
            db=db,
            user_id=auth_data.get("user_id"),
            days=days,
            skip=skip,
            limit=limit
        )
        return success_response(
            data={
                "sessions": sessions,
                "total_count": len(sessions),
                "skip": skip,
                "limit": limit,
                "days": days
            },
            message="Recent sessions retrieved successfully"
        )
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.get("/user/sessions/search", response_model=ResponseModel)
async def search_sessions(
    q: str,
    skip: int = 0,
    limit: int = 100,
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Search chat sessions for the logged-in user"""
    try:
        sessions = await chat_service.search_sessions(
            db=db,
            user_id=auth_data.get("user_id"),
            search_term=q,
            skip=skip,
            limit=limit
        )
        return success_response(
            data={
                "sessions": sessions,
                "total_count": len(sessions),
                "skip": skip,
                "limit": limit,
                "search_term": q
            },
            message="Search completed successfully"
        )
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.put("/session/{session_id}/star", response_model=ResponseModel)
async def star_unstar_session(
    session_id: str,
    is_starred: bool,
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Star or unstar a chat session"""
    try:
        success = await chat_service.update_session_star(
            db=db,
            session_id=session_id,
            is_starred=is_starred,
            auth_data=auth_data
        )
        if success:
            action = "starred" if is_starred else "unstarred"
            return success_response(message=f"Session {action} successfully")
        else:
            return fail_response(message="Failed to update session star status", status_code=400)
    except ValueError as e:
        return fail_response(message=str(e), status_code=404)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.put("/session/{session_id}", response_model=ResponseModel)
async def update_session(
    session_id: str,
    update_data: ChatSessionUpdateSchema,
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Update a chat session (name, starred status, etc.)"""
    try:
        success = True
        
        if update_data.chat_name is not None:
            success = await chat_service.update_session_name(
                db=db,
                session_id=session_id,
                chat_name=update_data.chat_name,
                auth_data=auth_data
            )
        
        if success and update_data.is_starred is not None:
            success = await chat_service.update_session_star(
                db=db,
                session_id=session_id,
                is_starred=update_data.is_starred,
                auth_data=auth_data
            )
        
        if success:
            return success_response(message="Session updated successfully")
        else:
            return fail_response(message="Failed to update session", status_code=400)
    except ValueError as e:
        return fail_response(message=str(e), status_code=404)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.delete("/session/{session_id}", response_model=ResponseModel)
async def delete_session(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Delete a chat session"""
    try:
        success = await chat_service.delete_session(
            db=db,
            session_id=session_id,
            auth_data=auth_data
        )
        if success:
            return success_response(message="Session deleted successfully")
        else:
            return fail_response(message="Failed to delete session", status_code=400)
    except ValueError as e:
        return fail_response(message=str(e), status_code=404)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.put("/message/{message_id}", response_model=ResponseModel)
async def update_message(
    message_id: int,
    update_data: ChatMessageUpdateSchema,
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Update a chat message"""
    try:
        updated_message = await chat_service.update_message(
            db=db,
            message_id=message_id,
            message=update_data.message,
            auth_data=auth_data
        )
        if updated_message:
            return success_response(data=updated_message, message="Message updated successfully")
        else:
            return fail_response(message="Message not found or access denied", status_code=404)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)

@router.delete("/message/{message_id}", response_model=ResponseModel)
async def delete_message(
    message_id: int,
    chat_service: ChatService = Depends(get_chat_service),
    auth_data: Dict[str, Any] = Depends(authenticate_user),
    plant_context: dict = Depends(validate_plant_access_middleware),
    db: AsyncSession = Depends(get_plant_db_with_context)
) -> Any:
    """Delete a chat message"""
    try:
        success = await chat_service.delete_message(
            db=db,
            message_id=message_id,
            auth_data=auth_data
        )
        if success:
            return success_response(message="Message deleted successfully")
        else:
            return fail_response(message="Message not found or access denied", status_code=404)
    except Exception as e:
        return fail_response(message=str(e), status_code=500)