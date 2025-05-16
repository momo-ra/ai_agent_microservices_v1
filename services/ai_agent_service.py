from dotenv import load_dotenv
import os
import httpx
import json
from database import AsyncSessionLocal
from utils.log import setup_logger
import uuid
from queries.chat_session_queries import *
from queries.chat_message_queries import *
from typing import List, Dict, Any, Optional
from models.models import ChatMessage
from datetime import datetime
from queries.ai_agent_queries import execute_query_in_database
from serializers import format_api_response, format_history_response

logger = setup_logger(__name__)

load_dotenv()

AI_AGENT_URL = "https://f27d-151-84-208-157.ngrok-free.app/ai-agent/chat"

class ChatService:
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=180.0)
    
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
                # Update session timestamp
                await update_chat_session(session_id=session_id)
                
                # Get SQL query from AI service
                ai_request = {"input": message}
                starttime = datetime.now()
                query = None
                
                try:
                    query = await self.get_ai_response(ai_request)
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

                # Execute the query if we got one back
                result = None
                execution_time = (datetime.now() - starttime).total_seconds()
                
                if query:
                    try:
                        result = await execute_query_in_database(query, session)
                        logger.info(f'Query returned {len(result) if result else 0} rows')
                    except Exception as e:
                        logger.error(f'Error executing query: {e}')
                        error_response = {
                            "session_id": session_id,
                            "message": message,
                            "response": [],
                            "timestamp": datetime.now().isoformat(),
                            "error": {
                                "type": "query_execution_error",
                                "message": "Failed to execute database query. Please try a different question."
                            }
                        }
                        
                        await create_chat_message(
                            session_id=session_id,
                            message=message,
                            execution_time=execution_time,
                            response=json.dumps([]),
                            query=f"Error executing query: {str(e)[:200]}"
                        )
                        
                        return error_response
                else:
                    # No query was returned, but no error was raised
                    error_response = {
                        "session_id": session_id,
                        "message": message,
                        "response": [],
                        "timestamp": datetime.now().isoformat(),
                        "error": {
                            "type": "invalid_query",
                            "message": "Unable to generate a valid query for your question. Please try rephrasing it."
                        }
                    }
                    
                    await create_chat_message(
                        session_id=session_id,
                        message=message,
                        execution_time=execution_time,
                        response=json.dumps([]),
                        query="No query generated"
                    )
                    
                    return error_response
                
                # Format response using serializer
                response = format_api_response(session_id, message, result)
                
                # Store response in database (as JSON string)
                json_response = json.dumps(response["response"])
                await create_chat_message(
                    session_id=session_id,
                    message=message,
                    execution_time=execution_time,
                    response=json_response,
                    query=query
                )
                
                logger.success(f'Message processed: {message}')
                return response
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
    
    async def get_ai_response(self, context: Dict[str, Any]) -> Optional[str]:
        """Get SQL query from AI service"""
        try:
            logger.info(f'AI_AGENT_URL = {AI_AGENT_URL}')
            
            if not AI_AGENT_URL:
                logger.error('AI_AGENT_URL is not set!')
                raise ValueError("AI service URL is not configured")
            
            # زيادة مهلة الانتظار
            timeout = httpx.Timeout(180.0)  # 3 minutes
            
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
                        if isinstance(response_data, dict) and "query" in response_data:
                            logger.success('Received query from AI!')
                            return response_data["query"]
                        elif isinstance(response_data, str):
                            logger.success('Received query as string from AI!')
                            return response_data
                        else:
                            logger.error(f'Unexpected response format: {response_data}')
                    except Exception as json_error:
                        logger.error(f'Error parsing JSON response: {json_error}')
                        # التحقق من وجود استعلام SQL في الاستجابة النصية
                        if isinstance(response.text, str) and "SELECT" in response.text.upper():
                            logger.info('Response appears to contain SQL query, returning raw text')
                            return response.text
                else:
                    logger.error(f'Error from AI service: Status {response.status_code}, Response: {response.text[:200]}')
                    raise ValueError(f"AI service returned status: {response.status_code}")
                
            raise ValueError("Failed to get a valid response from the AI service")
                
        except Exception as e:
            logger.error(f'Failed to get AI response: {str(e)}')
            raise ValueError(str(e))