from dotenv import load_dotenv
import httpx
import json
from database import AsyncSessionLocal
from utils.log import setup_logger
import uuid
from queries.chat_session_queries import *
from queries.chat_message_queries import *
from typing import List, Dict, Any, Optional
from datetime import datetime
from serializers import format_history_response

logger = setup_logger(__name__)

load_dotenv()

AI_AGENT_URL = "https://1c62-151-84-208-157.ngrok-free.app/ai-agent/chat"

class ChatService:
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=1000.0)
    
    async def create_session(self) -> str:
        """Create a new chat session and return the session ID"""
        try:
            session_id = str(uuid.uuid4())
            created_session = await create_chat_session(session_id)
            if created_session:
                logger.success(f'Session created: {session_id}')
                return session_id
            else:
                logger.error('Failed to create session')
                raise ValueError("Failed to create session")
        except Exception as e:
            logger.error(f'Error creating session: {e}')
            raise e
        
    async def send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """Process user message, execute SQL query, and return results"""
        try:
            async with AsyncSessionLocal() as session:
                # Check if session exists, create if it doesn't
                session_exists = await get_chat_session(session_id)
                if not session_exists:
                    logger.warning(f"Session {session_id} does not exist, creating it now")
                    await create_chat_session(session_id)
                
                # Update session timestamp
                await update_chat_session(session_id=session_id)
                
                ai_request_schema = {
                    "input_message": message,
                    "session_id": session_id
                    }
                # Get response from AI service
                starttime = datetime.now()
                ai_response = None
                
                try:
                    ai_response = await self.get_ai_response(ai_request_schema)
                    print('----------------------------------')
                    print(ai_response)
                    print('----------------------------------')
                    execution_time = (datetime.now() - starttime).total_seconds()
                except Exception as e:
                    logger.error(f'Error getting AI response: {e}')
                    
                    # Create a friendly error response for the user
                    error_response = {
                        "session_id": session_id,
                        "message": message,
                        "response": [],
                        "timestamp": datetime.now().isoformat(),
                        "error": {
                            "type": "ai_service_unavailable",
                            "message": "The AI service is temporarily unavailable. Please try again later."
                        }
                    }
                    
                    # Still store this in the database
                    await create_chat_message(
                        session_id=session_id,
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
                        # Format response using the received data directly
                        response = {
                            "session_id": session_id,
                            "message": message,
                            "response": ai_response,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Store response in database (as JSON string)
                        json_response = json.dumps(ai_response)
                        await create_chat_message(
                            session_id=session_id,
                            message=message,
                            execution_time=execution_time,
                            response=json_response,
                            query="No query - direct response from AI service"
                        )
                        
                        logger.success(f'Message processed: {message}')
                        return response
                    except Exception as e:
                        logger.error(f'Error processing AI response: {e}')
                        error_response = {
                            "session_id": session_id,
                            "message": message,
                            "response": [],
                            "timestamp": datetime.now().isoformat(),
                            "error": {
                                "type": "response_processing_error",
                                "message": "Failed to process AI response. Please try a different question."
                            }
                        }
                        
                        await create_chat_message(
                            session_id=session_id,
                            message=message,
                            execution_time=execution_time,
                            response=json.dumps([]),
                            query=f"Error processing AI response: {str(e)[:200]}"
                        )
                        
                        return error_response
                else:
                    # No response was returned, but no error was raised
                    error_response = {
                        "session_id": session_id,
                        "message": message,
                        "response": [],
                        "timestamp": datetime.now().isoformat(),
                        "error": {
                            "type": "invalid_response",
                            "message": "Unable to generate a valid response for your question. Please try rephrasing it."
                        }
                    }
                    
                    await create_chat_message(
                        session_id=session_id,
                        message=message,
                        execution_time=execution_time,
                        response=json.dumps([]),
                        query="No response generated"
                    )
                    
                    return error_response
                
        except Exception as e:
            logger.error(f'Error processing message: {e}')
            # For any other unexpected error
            error_response = {
                "session_id": session_id,
                "message": message,
                "response": [],
                "timestamp": datetime.now().isoformat(),
                "error": {
                    "type": "internal_error",
                    "message": "An unexpected error occurred. Please try again later."
                }
            }
            
            try:
                await create_chat_message(
                    session_id=session_id,
                    message=message,
                    execution_time=0,
                    response=json.dumps([]),
                    query=f"Error: {str(e)[:200]}"
                )
            except Exception as db_error:
                logger.error(f"Failed to store error in database: {db_error}")
                
            return error_response
    
    async def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get the chat history for a session"""
        try:
            messages = await get_session_messages(session_id)
            logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
            
            # Use serializer to format each message
            history = [format_history_response(msg) for msg in messages]
            return history
        except Exception as e:
            logger.error(f'Error getting session history: {e}')
            raise e
    
    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a chat session"""
        try:
            session = await get_chat_session(session_id)
            if not session:
                raise ValueError(f"Session with id {session_id} not found")
                
            return {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat() if hasattr(session.created_at, 'isoformat') else str(session.created_at),
                "updated_at": session.updated_at.isoformat() if session.updated_at and hasattr(session.updated_at, 'isoformat') else None
            }
        except Exception as e:
            logger.error(f'Error getting session info: {e}')
            raise e
    
    async def get_ai_response(self, context: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Get response from AI service"""
        try:
            logger.info(f'AI_AGENT_URL = {AI_AGENT_URL}')
            
            if not AI_AGENT_URL:
                logger.error('AI_AGENT_URL is not set!')
                raise ValueError("AI service URL is not configured")
            
            # 3 minutes timeout
            timeout = httpx.Timeout(1000.0)
            
            logger.info('Starting AI request - this may take around 1 minute...')
            
            async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
                response = await client.post(
                    AI_AGENT_URL,
                    json=context,
                    headers={"Content-Type": "application/json"}
                )
                
                logger.info(f'Response status: {response.status_code}')
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        
                        # Handle the new schema format
                        if isinstance(response_data, list) and len(response_data) > 0:
                            logger.success('Received JSON response array from AI!')
                            return response_data
                        elif isinstance(response_data, dict):
                            logger.success('Received JSON response object from AI!')
                            return [response_data]  # Wrap single object in array for consistency
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