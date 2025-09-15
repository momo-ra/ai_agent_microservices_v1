from dotenv import load_dotenv
import httpx
import json
from sqlalchemy.ext.asyncio import AsyncSession
from utils.log import setup_logger
import uuid
from queries.chat_session_queries import (
    create_chat_session, get_chat_session, update_chat_session,
    get_user_sessions, get_starred_sessions, get_recent_sessions,
    search_sessions, update_session_star, update_session_name, delete_session
)
from queries.chat_message_queries import (
    create_chat_message, get_session_messages, update_chat_message, delete_chat_message
)
from typing import List, Dict, Any, Optional
from datetime import datetime
from serializers import format_history_response
from middlewares.permission_middleware import can_access_session
from schemas.schema import AiResponseSchema, AnswerType, PlotType, QuestionType
from services.artifact_service import ArtifactService

logger = setup_logger(__name__)

load_dotenv('.env', override=True)

AI_AGENT_URL = "https://653af10492df.ngrok-free.app/ai-agent/chat"

class ChatService:
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=1000.0)
        self.artifact_service = ArtifactService()
    
    async def create_session(self, db: AsyncSession, user_id: int) -> str:
        """Create a new chat session and return the session ID"""
        try:
            session_id = str(uuid.uuid4())
            created_session = await create_chat_session(db, session_id, user_id)
            if created_session:
                logger.success(f'Session created: {session_id}')
                return session_id
            else:
                logger.error('Failed to create session')
                raise ValueError("Failed to create session")
        except Exception as e:
            logger.error(f'Error creating session: {e}')
            raise e
        
    async def send_message(self, db: AsyncSession, session_id: str, message: str, auth_data: Dict[str, Any], plant_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user message, execute SQL query, and return results"""
        try:
            if not await can_access_session(db, session_id, auth_data):
                raise ValueError("Access denied: You do not have permission to access this session.")
            # Check if session exists, create if it doesn't
            session_exists = await get_chat_session(db, session_id)
            if not session_exists:
                logger.warning(f"Session {session_id} does not exist, creating it now")
                await create_chat_session(db, session_id, auth_data.get("user_id"))
            # Update session timestamp
            await update_chat_session(db, session_id=session_id)
            ai_request_schema = {
                "input_message": message,
                "session_id": session_id,
                "plant_id": plant_context.get("plant_id") if plant_context else None
            }
            # Get response from AI service
            starttime = datetime.now()
            ai_response = None
            try:
                ai_response = await self.get_ai_response(ai_request_schema, plant_id=plant_context.get("plant_id") if plant_context else None)
                execution_time = (datetime.now() - starttime).total_seconds()
            except Exception as e:
                logger.error(f'Error getting AI response: {e}')
                error_response = {
                    "session_id": session_id,
                    "message": message,
                    "response": [],
                    "artifacts": [],  # Include empty artifacts array for consistency
                    "timestamp": datetime.now().isoformat(),
                    "error": {
                        "type": "ai_service_unavailable",
                        "message": "The AI service is temporarily unavailable. Please try again later."
                    }
                }
                await create_chat_message(
                    db=db,
                    session_id=session_id,
                    user_id=auth_data.get("user_id"),
                    message=message,
                    execution_time=0,
                    response=json.dumps([]),
                    query="Error: AI service unavailable"
                )
                logger.warning(f'AI service unavailable, returning error response for message: {message}')
                return error_response
            execution_time = (datetime.now() - starttime).total_seconds()
            if ai_response:
                try:
                    response = {
                        "session_id": session_id,
                        "message": message,
                        "response": ai_response,
                        "timestamp": datetime.now().isoformat()
                    }
                    json_response = json.dumps(ai_response)
                    # Create chat message record
                    chat_message = await create_chat_message(
                        db=db,
                        session_id=session_id,
                        user_id=auth_data.get("user_id"),
                        message=message,
                        execution_time=execution_time,
                        response=json_response,
                        query="No query - direct response from AI service"
                    )
                    
                    # Try to create artifacts from AI response and collect them
                    created_artifacts = []
                    try:
                        for ai_item in ai_response:
                            artifact = await self.artifact_service.create_artifact_from_ai_response(
                                db=db,
                                session_id=session_id,
                                user_id=auth_data.get("user_id"),
                                ai_response=ai_item,
                                message_id=chat_message.get('id') if chat_message and isinstance(chat_message, dict) else None
                            )
                            if artifact:
                                created_artifacts.append(artifact)
                                logger.info(f"Created artifact: {artifact.get('title', 'Untitled')}")
                    except Exception as artifact_error:
                        logger.warning(f"Failed to create artifacts: {artifact_error}")
                        # Don't fail the main response if artifact creation fails
                    
                    # Include artifacts in the response for frontend consumption
                    response["artifacts"] = created_artifacts
                    
                    logger.success(f'Message processed: {message}')
                    return response
                except Exception as e:
                    logger.error(f'Error processing AI response: {e}')
                    error_response = {
                        "session_id": session_id,
                        "message": message,
                        "response": [],
                        "artifacts": [],  # Include empty artifacts array for consistency
                        "timestamp": datetime.now().isoformat(),
                        "error": {
                            "type": "response_processing_error",
                            "message": "Failed to process AI response. Please try a different question."
                        }
                    }
                    await create_chat_message(
                        db=db,
                        session_id=session_id,
                        user_id=auth_data.get("user_id"),
                        message=message,
                        execution_time=execution_time,
                        response=json.dumps([]),
                        query=f"Error processing AI response: {str(e)[:200]}"
                    )
                    return error_response
            else:
                error_response = {
                    "session_id": session_id,
                    "message": message,
                    "response": [],
                    "artifacts": [],  # Include empty artifacts array for consistency
                    "timestamp": datetime.now().isoformat(),
                    "error": {
                        "type": "invalid_response",
                        "message": "Unable to generate a valid response for your question. Please try rephrasing it."
                    }
                }
                await create_chat_message(
                    db=db,
                    session_id=session_id,
                    user_id=auth_data.get("user_id"),
                    message=message,
                    execution_time=execution_time,
                    response=json.dumps([]),
                    query="No response generated"
                )
                return error_response
        except Exception as e:
            logger.error(f'Error processing message: {e}')
            error_response = {
                "session_id": session_id,
                "message": message,
                "response": [],
                "artifacts": [],  # Include empty artifacts array for consistency
                "timestamp": datetime.now().isoformat(),
                "error": {
                    "type": "internal_error",
                    "message": "An unexpected error occurred. Please try again later."
                }
            }
            try:
                await create_chat_message(
                    db=db,
                    session_id=session_id,
                    user_id=auth_data.get("user_id"),
                    message=message,
                    execution_time=0,
                    response=json.dumps([]),
                    query=f"Error: {str(e)[:200]}"
                )
            except Exception as db_error:
                logger.error(f"Failed to store error in database: {db_error}")
            return error_response
    
    async def get_session_history(self, db: AsyncSession, session_id: str, auth_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get the chat history for a session"""
        try:
            if not await can_access_session(db, session_id, auth_data):
                raise ValueError("Access denied: You do not have permission to access this session.")
            messages = await get_session_messages(db, session_id)
            logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
            history = [format_history_response(msg) for msg in messages]
            return history
        except Exception as e:
            logger.error(f'Error getting session history: {e}')
            raise e
    
    async def get_session_info(self, db: AsyncSession, session_id: str, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about a chat session"""
        try:
            if not await can_access_session(db, session_id, auth_data):
                raise ValueError("Access denied: You do not have permission to access this session.")
            session_obj = await get_chat_session(db, session_id)
            if not session_obj:
                raise ValueError(f"Session with id {session_id} not found")
            return {
                "session_id": session_obj.session_id,
                "created_at": session_obj.created_at.isoformat() if hasattr(session_obj.created_at, 'isoformat') else str(session_obj.created_at),
                "updated_at": session_obj.updated_at.isoformat() if hasattr(session_obj, 'updated_at') and session_obj.updated_at and hasattr(session_obj.updated_at, 'isoformat') else None
            }
        except Exception as e:
            logger.error(f'Error getting session info: {e}')
            raise e
    
    async def get_user_sessions(self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all chat sessions for a user"""
        try:
            sessions = await get_user_sessions(db, user_id, skip, limit)
            return [self._format_session_response(session) for session in sessions]
        except Exception as e:
            logger.error(f'Error getting user sessions: {e}')
            raise e
    
    async def get_starred_sessions(self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get starred chat sessions for a user"""
        try:
            sessions = await get_starred_sessions(db, user_id, skip, limit)
            return [self._format_session_response(session) for session in sessions]
        except Exception as e:
            logger.error(f'Error getting starred sessions: {e}')
            raise e
    
    async def get_recent_sessions(self, db: AsyncSession, user_id: int, days: int = 7, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent chat sessions for a user"""
        try:
            sessions = await get_recent_sessions(db, user_id, days, skip, limit)
            return [self._format_session_response(session) for session in sessions]
        except Exception as e:
            logger.error(f'Error getting recent sessions: {e}')
            raise e
    
    async def search_sessions(self, db: AsyncSession, user_id: int, search_term: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Search chat sessions for a user"""
        try:
            sessions = await search_sessions(db, user_id, search_term, skip, limit)
            return [self._format_session_response(session) for session in sessions]
        except Exception as e:
            logger.error(f'Error searching sessions: {e}')
            raise e
    
    async def update_session_star(self, db: AsyncSession, session_id: str, is_starred: bool, auth_data: Dict[str, Any]) -> bool:
        """Update starred status of a chat session"""
        try:
            if not await can_access_session(db, session_id, auth_data):
                raise ValueError("Access denied: You do not have permission to access this session.")
            await update_session_star(db, session_id, is_starred)
            return True
        except Exception as e:
            logger.error(f'Error updating session star status: {e}')
            raise e
    
    async def update_session_name(self, db: AsyncSession, session_id: str, chat_name: str, auth_data: Dict[str, Any]) -> bool:
        """Update name of a chat session"""
        try:
            if not await can_access_session(db, session_id, auth_data):
                raise ValueError("Access denied: You do not have permission to access this session.")
            await update_session_name(db, session_id, chat_name)
            return True
        except Exception as e:
            logger.error(f'Error updating session name: {e}')
            raise e
    
    async def delete_session(self, db: AsyncSession, session_id: str, auth_data: Dict[str, Any]) -> bool:
        """Delete a chat session"""
        try:
            if not await can_access_session(db, session_id, auth_data):
                raise ValueError("Access denied: You do not have permission to access this session.")
            await delete_session(db, session_id)
            return True
        except Exception as e:
            logger.error(f'Error deleting session: {e}')
            raise e
    
    async def update_message(self, db: AsyncSession, message_id: int, message: str, auth_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a chat message"""
        try:
            user_id = auth_data.get("user_id")
            updated_message = await update_chat_message(db, message_id, message, user_id)
            return updated_message
        except Exception as e:
            logger.error(f'Error updating message: {e}')
            raise e
    
    async def delete_message(self, db: AsyncSession, message_id: int, auth_data: Dict[str, Any]) -> bool:
        """Delete a chat message"""
        try:
            user_id = auth_data.get("user_id")
            return await delete_chat_message(db, message_id, user_id)
        except Exception as e:
            logger.error(f'Error deleting message: {e}')
            raise e
    
    def _format_session_response(self, session) -> Dict[str, Any]:
        """Format session response with additional metadata"""
        try:
            # Get last message info if available
            last_message = None
            last_message_time = None
            message_count = 0
            
            # This would need to be optimized with a proper join query in production
            # For now, we'll set basic info
            return {
                "id": session.id,
                "session_id": session.session_id,
                "user_id": session.user_id,
                "user_name": session.user_name,
                "chat_name": session.chat_name,
                "is_starred": session.is_starred,
                "created_at": session.created_at.isoformat() if hasattr(session.created_at, 'isoformat') else str(session.created_at),
                "updated_at": session.updated_at.isoformat() if hasattr(session.updated_at, 'isoformat') else str(session.updated_at),
                "message_count": message_count,
                "last_message": last_message,
                "last_message_time": last_message_time
            }
        except Exception as e:
            logger.error(f'Error formatting session response: {e}')
            return {
                "id": session.id,
                "session_id": session.session_id,
                "user_id": session.user_id,
                "user_name": session.user_name,
                "chat_name": session.chat_name,
                "is_starred": session.is_starred,
                "created_at": session.created_at.isoformat() if hasattr(session.created_at, 'isoformat') else str(session.created_at),
                "updated_at": session.updated_at.isoformat() if hasattr(session.updated_at, 'isoformat') else str(session.updated_at),
                "message_count": 0,
                "last_message": None,
                "last_message_time": None
            }

    async def get_ai_response(self, context: Dict[str, Any], plant_id: str = None) -> Optional[List[Dict[str, Any]]]:
        """Get response from AI service"""
        try:
            logger.info(f'AI_AGENT_URL = {AI_AGENT_URL}')
            
            if not AI_AGENT_URL:
                logger.error('AI_AGENT_URL is not set!')
                raise ValueError("AI service URL is not configured")
            
            # 3 minutes timeout
            timeout = httpx.Timeout(1000.0)
            
            logger.info('Starting AI request - this may take around 1 minute...')
            
            # Prepare headers
            headers = {"Content-Type": "application/json"}
            if plant_id:
                headers["Plant-Id"] = plant_id
                logger.info(f'Sending Plant-Id header: {plant_id}')
            else:
                logger.warning('No plant_id provided for AI request')
            
            async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
                response = await client.post(
                    AI_AGENT_URL,
                    json=context,
                    headers=headers
                )
                
                logger.info(f'Response status: {response.status_code}')
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        
                        # Handle the new schema format
                        if isinstance(response_data, list) and len(response_data) > 0:
                            logger.success('Received JSON response array from AI!')
                            # Validate each response against the schema
                            validated_responses = []
                            for item in response_data:
                                try:
                                    # Try to parse as AiResponseSchema
                                    validated_item = AiResponseSchema(**item)
                                    validated_responses.append(validated_item.dict())
                                except Exception as validation_error:
                                    logger.warning(f"Response item validation failed: {validation_error}")
                                    # Fallback to original item if validation fails
                                    validated_responses.append(item)
                            return validated_responses
                        elif isinstance(response_data, dict):
                            logger.success('Received JSON response object from AI!')
                            try:
                                # Try to parse as AiResponseSchema
                                validated_item = AiResponseSchema(**response_data)
                                return [validated_item.dict()]
                            except Exception as validation_error:
                                logger.warning(f"Response validation failed: {validation_error}")
                                # Fallback to original response if validation fails
                                return [response_data]
                        else:
                            logger.error(f'Unexpected response format: {response_data}')
                            raise ValueError("AI service returned an invalid response format")
                    except Exception as json_error:
                        logger.error(f'Error parsing JSON response: {json_error}')
                        raise ValueError(f"Failed to parse AI service response: {str(json_error)}")
                else:
                    logger.error(f'Error from AI service: Status {response.status_code}, Response: {response.text[:200]}')
                    raise ValueError(f"AI service returned status: {response.status_code}")
                
            raise ValueError("Failed to get a valid response from the AI service")
                
        except Exception as e:
            logger.error(f'Failed to get AI response: {str(e)}')
            raise ValueError(str(e))