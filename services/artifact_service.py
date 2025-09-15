from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from queries.artifact_queries import (
    create_artifact,
    get_artifact_by_id,
    get_artifacts_by_session,
    get_artifacts_count_by_session,
    update_artifact,
    delete_artifact,
    get_artifacts_by_type,
    search_artifacts,
    get_all_user_artifacts,
    get_user_artifacts_count,
    get_user_artifacts_by_type,
    search_user_artifacts
)
from schemas.schema import (
    ArtifactCreateSchema,
    ArtifactResponseSchema,
    ArtifactUpdateSchema,
    ArtifactListResponseSchema,
    ArtifactType
)
from utils.log import setup_logger
from middlewares.permission_middleware import can_access_session
import json

logger = setup_logger(__name__)

class ArtifactService:
    def __init__(self):
        pass
    
    async def create_artifact_from_ai_response(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: int,
        ai_response: Dict[str, Any],
        message_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Create artifacts from AI response data"""
        try:
            # Check if AI response contains artifact data
            if not self._has_artifact_data(ai_response):
                logger.info("No artifact data found in AI response")
                return None
            
            # Extract artifact information from AI response
            artifact_data = self._extract_artifact_data(ai_response)
            
            if not artifact_data:
                logger.info("Could not extract artifact data from AI response")
                return None
            
            # Create artifact
            artifact = await create_artifact(
                db=db,
                session_id=session_id,
                user_id=user_id,
                title=artifact_data.get("title", "AI Generated Artifact"),
                content=artifact_data.get("content", ""),
                artifact_type=artifact_data.get("type", "general"),
                artifact_metadata=artifact_data.get("metadata"),
                message_id=message_id
            )
            
            if artifact:
                logger.success(f"Created artifact {artifact.id} from AI response")
                return self._format_artifact_response(artifact)
            
            return None
        except Exception as e:
            logger.error(f"Error creating artifact from AI response: {e}")
            return None
    
    def _has_artifact_data(self, ai_response: Dict[str, Any]) -> bool:
        """Check if AI response contains artifact data"""
        # Check if AI response has specific types that should create artifacts
        plot_type = ai_response.get("plot_type")
        answer_type = ai_response.get("answer_type")
        question_type = ai_response.get("question_type")
        
        # Get the data field to check if it's empty (indicating an error)
        data = ai_response.get("data", [])
        
        # If any of these types exist AND there's actual data, create an artifact
        if (plot_type or answer_type or question_type) and data:
            return True
        
        # Also check for content-based indicators
        content = ai_response.get("answer", "").lower()
        artifact_indicators = [
            "artifact", "export", "code", "diagram", "chart", 
            "implementation", "example", "template", "structure",
            "plot", "graph", "data", "analysis", "```", "function", "class"
        ]
        
        # Only create artifact if there's meaningful content AND (data OR substantial content)
        has_content_indicators = any(indicator in content for indicator in artifact_indicators)
        has_substantial_content = len(content.strip()) > 50
        
        # For content-based artifacts (code, diagrams, etc.), allow if there's substantial content
        # For data-based artifacts (plots, charts), require actual data
        if has_content_indicators:
            # Check for content-based indicators that don't require data
            content_based_indicators = ['code', 'diagram', 'chart', 'implementation', 'example', 'template', 'artifact', 'export', '```', 'function', 'class']
            if any(indicator in content for indicator in content_based_indicators):
                return has_substantial_content
            else:
                # For data-based indicators, require actual data
                return data and has_substantial_content
        
        return False
    
    def _is_error_response(self, ai_response: Dict[str, Any]) -> bool:
        """Check if the AI response appears to be an error or failed response"""
        # Check for empty data field (main indicator of error)
        data = ai_response.get("data", [])
        if not data:
            return True
        
        # Check for error indicators in the answer
        answer = ai_response.get("answer", "").lower()
        error_indicators = [
            "error", "failed", "exception", "not found", "no data", 
            "unable to", "cannot", "invalid", "missing", "empty"
        ]
        
        # If answer contains error indicators, it's likely an error
        if any(indicator in answer for indicator in error_indicators):
            return True
        
        # Check if answer is too short (likely an error message)
        if len(answer.strip()) < 20:
            return True
        
        return False
    
    def _extract_artifact_data(self, ai_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract artifact data from AI response"""
        try:
            answer = ai_response.get("answer", "")
            ai_data = ai_response.get("data", [])
            
            # Additional validation: Don't create artifacts for empty responses
            if not answer.strip() and not ai_data:
                logger.info("Skipping artifact creation: empty answer and no data")
                return None
            
            # Check if this looks like an error response
            if self._is_error_response(ai_response):
                logger.info("Skipping artifact creation: appears to be an error response")
                return None
            
            # Try to extract title from the response
            title = self._extract_title(answer)
            
            # Determine artifact type based on AI response data
            artifact_type = self._determine_artifact_type(ai_response)
            
            # Extract the main content (could be code, diagram, etc.)
            content = self._extract_content(answer, artifact_type, ai_data)
            
            # Create metadata with all AI response data
            metadata = {
                "source": "ai_response",
                "answer_type": ai_response.get("answer_type"),
                "question_type": ai_response.get("question_type"),
                "plot_type": ai_response.get("plot_type"),
                "rewritten_question": ai_response.get("rewritten_question"),
                "data": ai_data  # Include the data field if present
            }
            
            return {
                "title": title,
                "content": content,
                "type": artifact_type,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"Error extracting artifact data: {e}")
            return None
    
    def _extract_title(self, answer: str) -> str:
        """Extract a title from the AI response"""
        # Look for common title patterns
        lines = answer.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and not line.startswith('#') and len(line) < 100:
                # Remove common prefixes
                title = line.replace('Title:', '').replace('Name:', '').strip()
                if title:
                    return title[:100]  # Limit title length
        return "AI Generated Artifact"
    
    def _determine_artifact_type(self, ai_response: Dict[str, Any]) -> str:
        """Determine artifact type based on AI response data"""
        # First check plot_type (highest priority)
        plot_type = ai_response.get("plot_type")
        if plot_type:
            return plot_type.value if hasattr(plot_type, 'value') else str(plot_type)
        
        # Then check answer_type
        answer_type = ai_response.get("answer_type")
        if answer_type:
            return answer_type.value if hasattr(answer_type, 'value') else str(answer_type)
        
        # Then check question_type
        question_type = ai_response.get("question_type")
        if question_type:
            return question_type.value if hasattr(question_type, 'value') else str(question_type)
        
        # Finally, check content for code/diagram patterns
        answer = ai_response.get("answer", "").lower()
        if any(keyword in answer for keyword in ['```', 'function', 'class', 'import', 'const', 'let', 'var']):
            return ArtifactType.CODE
        elif any(keyword in answer for keyword in ['diagram', 'flowchart', 'graph', 'chart']):
            return ArtifactType.DIAGRAM
        elif any(keyword in answer for keyword in ['data', 'table', 'json', 'csv', 'array']):
            return ArtifactType.DATA
        elif any(keyword in answer for keyword in ['document', 'report', 'summary']):
            return ArtifactType.DOCUMENT
        else:
            return ArtifactType.GENERAL
    
    def _extract_content(self, answer: str, artifact_type: str, ai_data: Optional[List[Dict[str, Any]]] = None) -> str:
        """Extract the main content based on artifact type"""
        import re
        import json
        
        # For plot types, include both answer and any data
        if artifact_type in [ArtifactType.BAR_PLOT, ArtifactType.LINE_PLOT, 
                           ArtifactType.SCATTER_PLOT, ArtifactType.HISTOGRAM_PLOT, 
                           ArtifactType.PIE_PLOT]:
            content = answer.strip()
            if ai_data:
                content += f"\n\nData: {json.dumps(ai_data, indent=2)}"
            return content
        
        # For code artifacts, extract code blocks
        elif artifact_type == ArtifactType.CODE:
            code_blocks = re.findall(r'```[\s\S]*?```', answer)
            if code_blocks:
                return '\n'.join(code_blocks)
            return answer.strip()
        
        # For diagram artifacts, look for diagram content
        elif artifact_type == ArtifactType.DIAGRAM:
            return answer.strip()
        
        # For data artifacts, include structured data if available
        elif artifact_type == ArtifactType.DATA:
            content = answer.strip()
            if ai_data:
                content += f"\n\nStructured Data: {json.dumps(ai_data, indent=2)}"
            return content
        
        # For all other types, return the full answer
        else:
            return answer.strip()
    
    def _format_artifact_response(self, artifact) -> Dict[str, Any]:
        """Format artifact for response"""
        return {
            "id": artifact.id,
            "session_id": artifact.session_id,
            "user_id": artifact.user_id,
            "title": artifact.title,
            "artifact_type": artifact.artifact_type,
            "content": artifact.content,
            "artifact_metadata": artifact.artifact_metadata,
            "is_active": artifact.is_active,
            "message_id": artifact.message_id,
            "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
            "updated_at": artifact.updated_at.isoformat() if artifact.updated_at else None
        }
    
    async def create_artifact(
        self,
        db: AsyncSession,
        artifact_data: ArtifactCreateSchema,
        user_id: int,
        auth_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a new artifact"""
        try:
            # Check if user has access to the session
            if not await can_access_session(db, artifact_data.session_id, auth_data):
                logger.warning(f"User {user_id} does not have access to session {artifact_data.session_id}")
                return None
            
            artifact = await create_artifact(
                db=db,
                session_id=artifact_data.session_id,
                user_id=user_id,
                title=artifact_data.title,
                content=artifact_data.content,
                artifact_type=artifact_data.artifact_type.value,
                artifact_metadata=artifact_data.artifact_metadata,
                message_id=artifact_data.message_id
            )
            
            if artifact:
                return self._format_artifact_response(artifact)
            return None
        except Exception as e:
            logger.error(f"Error creating artifact: {e}")
            return None
    
    async def get_artifact(
        self,
        db: AsyncSession,
        artifact_id: int,
        user_id: int,
        auth_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get an artifact by ID"""
        try:
            artifact = await get_artifact_by_id(db, artifact_id, user_id)
            if artifact:
                # Check if user has access to the session
                if not await can_access_session(db, artifact.session_id, auth_data):
                    logger.warning(f"User {user_id} does not have access to session {artifact.session_id}")
                    return None
                return self._format_artifact_response(artifact)
            return None
        except Exception as e:
            logger.error(f"Error getting artifact {artifact_id}: {e}")
            return None
    
    async def get_session_artifacts(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: int,
        auth_data: Dict[str, Any],
        skip: int = 0,
        limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        """Get all artifacts for a session"""
        try:
            # Check if user has access to the session
            if not await can_access_session(db, session_id, auth_data):
                logger.warning(f"User {user_id} does not have access to session {session_id}")
                return None
            
            artifacts = await get_artifacts_by_session(db, session_id, user_id, skip, limit)
            total_count = await get_artifacts_count_by_session(db, session_id, user_id)
            
            formatted_artifacts = [self._format_artifact_response(artifact) for artifact in artifacts]
            
            return {
                "artifacts": formatted_artifacts,
                "total_count": total_count,
                "session_id": session_id
            }
        except Exception as e:
            logger.error(f"Error getting artifacts for session {session_id}: {e}")
            return None
    
    async def update_artifact(
        self,
        db: AsyncSession,
        artifact_id: int,
        user_id: int,
        update_data: ArtifactUpdateSchema,
        auth_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an artifact"""
        try:
            # First get the artifact to check session access
            artifact = await get_artifact_by_id(db, artifact_id, user_id)
            if not artifact:
                return None
            
            # Check if user has access to the session
            if not await can_access_session(db, artifact.session_id, auth_data):
                logger.warning(f"User {user_id} does not have access to session {artifact.session_id}")
                return None
            
            updated_artifact = await update_artifact(
                db=db,
                artifact_id=artifact_id,
                user_id=user_id,
                title=update_data.title,
                content=update_data.content,
                artifact_metadata=update_data.artifact_metadata,
                is_active=update_data.is_active
            )
            
            if updated_artifact:
                return self._format_artifact_response(updated_artifact)
            return None
        except Exception as e:
            logger.error(f"Error updating artifact {artifact_id}: {e}")
            return None
    
    async def delete_artifact(
        self,
        db: AsyncSession,
        artifact_id: int,
        user_id: int,
        auth_data: Dict[str, Any]
    ) -> bool:
        """Delete an artifact"""
        try:
            # First get the artifact to check session access
            artifact = await get_artifact_by_id(db, artifact_id, user_id)
            if not artifact:
                return False
            
            # Check if user has access to the session
            if not await can_access_session(db, artifact.session_id, auth_data):
                logger.warning(f"User {user_id} does not have access to session {artifact.session_id}")
                return False
            
            return await delete_artifact(db, artifact_id, user_id)
        except Exception as e:
            logger.error(f"Error deleting artifact {artifact_id}: {e}")
            return False
    
    async def search_artifacts(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: int,
        search_term: str,
        auth_data: Dict[str, Any],
        skip: int = 0,
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """Search artifacts in a session"""
        try:
            # Check if user has access to the session
            if not await can_access_session(db, session_id, auth_data):
                logger.warning(f"User {user_id} does not have access to session {session_id}")
                return None
            
            artifacts = await search_artifacts(db, session_id, user_id, search_term, skip, limit)
            return [self._format_artifact_response(artifact) for artifact in artifacts]
        except Exception as e:
            logger.error(f"Error searching artifacts in session {session_id}: {e}")
            return None
    
    # =============================================================================
    # USER ARTIFACTS METHODS (across all sessions)
    # =============================================================================
    
    async def get_all_user_artifacts(
        self,
        db: AsyncSession,
        user_id: int,
        auth_data: Dict[str, Any],
        skip: int = 0,
        limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        """Get all artifacts for a user across all sessions"""
        try:
            artifacts = await get_all_user_artifacts(db, user_id, skip, limit)
            total_count = await get_user_artifacts_count(db, user_id)
            
            formatted_artifacts = [self._format_artifact_response(artifact) for artifact in artifacts]
            
            return {
                "artifacts": formatted_artifacts,
                "total_count": total_count,
                "user_id": user_id
            }
        except Exception as e:
            logger.error(f"Error getting all artifacts for user {user_id}: {e}")
            return None
    
    async def get_user_artifacts_by_type(
        self,
        db: AsyncSession,
        user_id: int,
        artifact_type: str,
        auth_data: Dict[str, Any],
        skip: int = 0,
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """Get user artifacts by type across all sessions"""
        try:
            artifacts = await get_user_artifacts_by_type(db, user_id, artifact_type, skip, limit)
            return [self._format_artifact_response(artifact) for artifact in artifacts]
        except Exception as e:
            logger.error(f"Error getting {artifact_type} artifacts for user {user_id}: {e}")
            return None
    
    async def search_user_artifacts(
        self,
        db: AsyncSession,
        user_id: int,
        search_term: str,
        auth_data: Dict[str, Any],
        skip: int = 0,
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """Search user artifacts across all sessions"""
        try:
            artifacts = await search_user_artifacts(db, user_id, search_term, skip, limit)
            return [self._format_artifact_response(artifact) for artifact in artifacts]
        except Exception as e:
            logger.error(f"Error searching artifacts for user {user_id}: {e}")
            return None
