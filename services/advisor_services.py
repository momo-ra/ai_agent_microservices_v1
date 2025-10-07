from sqlalchemy.ext.asyncio import AsyncSession
from utils.log import setup_logger
from queries.advisor_queries import get_advisor_data, get_related_tags
from queries.chat_session_queries import create_chat_session, get_chat_session, update_chat_session
from queries.chat_message_queries import create_chat_message
from schemas.schema import (
    AdvisorRequestSchema, AdvisorResponseSchema, AdvisorNameIdsRequestSchema,
    AdvisorCalcEngineResultSchema, AdvisorCalcRequestWithTargetsSchema,
    AdvisorCompleteRequestSchema, ManualAiRequestSchema, QuestionType, AiResponseSchema,
    AdvisorSimpleRequestSchema, RecommendationCalculationEngineSchema,
    ArtifactCreateSchema, ArtifactType
)
from services.calculation_engine_services import build_execute_recommendation_query, finish_calc_engine_request, update_pairs, build_recommendation_schema
from services.artifact_service import ArtifactService
from typing import Dict, Any, Optional, List, Tuple
import json
import httpx
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime

load_dotenv('.env', override=True)

AI_AGENT_URL = "http://38.128.233.128:8000/ai-agent/manual"

logger = setup_logger(__name__)

class AdvisorService:
    """Service for handling advisor-related operations"""
    
    def __init__(self):
        self.logger = logger
        self.artifact_service = ArtifactService()
    
    async def process_advisor_request(
        self, 
        db: AsyncSession, 
        request_data: AdvisorRequestSchema
    ) -> Optional[AdvisorResponseSchema]:
        """
        Process advisor request and return response with variables containing lists of tags.
        
        Args:
            db: Database session
            request_data: Advisor request data containing tag_id, target_value, and unit_of_measure
        
        Returns:
            AdvisorResponseSchema with variables containing lists of tags
        """
        try:
            self.logger.info(f'Processing advisor request for tag: {request_data.tag_id}')
            
            # Get tag data from database
            tag_data = await get_advisor_data(
                db, 
                request_data.tag_id, 
                request_data.target_value, 
                request_data.unit_of_measure
            )
            
            if not tag_data:
                self.logger.error(f'No data found for tag: {request_data.tag_id}')
                return None
            
            # Get related tags for context
            related_tags = await get_related_tags(db, tag_data.get("plant_id"), request_data.tag_id)
            
            # Prepare data for external function call
            external_function_data = {
                "tag_info": tag_data,
                "related_tags": related_tags or [],
                "target_value": request_data.target_value,
                "unit_of_measure": request_data.unit_of_measure
            }
            
            # Call external function (placeholder - you will implement this later)
            external_response = await self._call_external_advisor_function(external_function_data)
            
            if not external_response:
                self.logger.error('External advisor function returned no response')
                return None
            
            # Parse the external response into the expected format
            advisor_response = self._parse_external_response(external_response)
            
            self.logger.success(f'Successfully processed advisor request for tag: {request_data.tag_id}')
            return advisor_response
            
        except Exception as e:
            self.logger.error(f'Error processing advisor request: {e}')
            raise e
    
    async def _call_external_advisor_function(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Call external advisor function with the prepared data.
        This is a placeholder function - you will implement the actual external call later.
        
        Args:
            data: Data to send to external function
        
        Returns:
            Response from external function
        """
        try:
            self.logger.info('Calling external advisor function (placeholder)')
            
            # TODO: Implement actual external function call here
            # For now, return a mock response structure
            mock_response = {
                "variable1": ["tag_001", "tag_002", "tag_003"],
                "variable2": ["tag_004", "tag_005"],
                "variable3": ["tag_006", "tag_007", "tag_008", "tag_009"],
                "recommendations": ["tag_010", "tag_011"],
                "warnings": ["tag_012"]
            }
            
            self.logger.info('External advisor function returned mock response')
            return mock_response
            
        except Exception as e:
            self.logger.error(f'Error calling external advisor function: {e}')
            raise e
    
    def _parse_external_response(self, external_response: Dict[str, Any]) -> AdvisorResponseSchema:
        """
        Parse external function response into AdvisorResponseSchema format.
        
        Args:
            external_response: Response from external function
        
        Returns:
            Parsed AdvisorResponseSchema
        """
        try:
            self.logger.info('Parsing external advisor response')
            
            # Ensure all values in the response are lists of strings (tag IDs)
            variables = {}
            for key, value in external_response.items():
                if isinstance(value, list):
                    # Ensure all items in the list are strings
                    variables[key] = [str(item) for item in value]
                else:
                    # Convert single values to list
                    variables[key] = [str(value)]
            
            response = AdvisorResponseSchema(variables=variables)
            
            self.logger.success(f'Parsed response with {len(variables)} variables')
            return response
            
        except Exception as e:
            self.logger.error(f'Error parsing external response: {e}')
            raise e
    
    async def validate_request(self, request_data: AdvisorRequestSchema) -> bool:
        """
        Validate advisor request data.
        
        Args:
            request_data: Request data to validate
        
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check if tag_id is provided and not empty
            if not request_data.tag_id or not request_data.tag_id.strip():
                self.logger.error('Tag ID is required and cannot be empty')
                return False
            
            # Check if target_value is a valid number
            if not isinstance(request_data.target_value, (int, float)):
                self.logger.error('Target value must be a number')
                return False
            
            # Check if unit_of_measure is provided and not empty
            if not request_data.unit_of_measure or not request_data.unit_of_measure.strip():
                self.logger.error('Unit of measure is required and cannot be empty')
                return False
            
            self.logger.info('Advisor request validation passed')
            return True
            
        except Exception as e:
            self.logger.error(f'Error validating request: {e}')
            return False
    
    async def get_calc_engine_result(
        self, 
        name_ids: List[str],
        plant_id: str
    ) -> Optional[AdvisorCalcEngineResultSchema]:
        """
        Get calculation engine result from name_ids.
        
        Args:
            name_ids: List of name IDs to analyze
            plant_id: Plant ID for the calculation
        
        Returns:
            AdvisorCalcEngineResultSchema with dependent and independent variables
        """
        try:
            self.logger.info(f'Getting calc engine result for name_ids: {name_ids}')
            
            # Validate plant_id parameter
            if not plant_id:
                self.logger.error("Plant ID is required")
                return None
            
            # Call the calculation engine service
            targets, dependent_variables, independent_variables = await build_execute_recommendation_query(
                name_ids, plant_id
            )
            
            result = AdvisorCalcEngineResultSchema(
                dependent_variables=dependent_variables,
                independent_variables=independent_variables,
                targets=targets
            )
            
            self.logger.success(f'Successfully got calc engine result for {len(name_ids)} name_ids')
            return result
            
        except Exception as e:
            self.logger.error(f'Error getting calc engine result: {e}')
            raise e
    
    async def get_calc_engine_result_with_session(
        self, 
        name_ids: List[str],
        plant_id: str,
        user_id: int,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        Get calculation engine result from name_ids, create session and artifact.
        
        Args:
            name_ids: List of name IDs to analyze
            plant_id: Plant ID for the calculation
            user_id: User ID creating the session
            db: Database session
        
        Returns:
            Dict with session_id, artifact_id, and calc engine result data
        """
        try:
            self.logger.info(f'Getting calc engine result with session for name_ids: {name_ids}')
            
            # Get calculation engine result
            result = await self.get_calc_engine_result(name_ids, plant_id)
            
            if not result:
                return None
            
            # Create new chat session
            session_id = str(uuid.uuid4())
            created_session = await create_chat_session(db, session_id, user_id)
            if not created_session:
                self.logger.error('Failed to create session')
                return None
            
            self.logger.success(f'Session created: {session_id}')
            
            # Prepare artifact content with calc engine result
            artifact_content = json.dumps({
                "dependent_variables": [var.dict() for var in result.dependent_variables],
                "independent_variables": [var.dict() for var in result.independent_variables],
                "targets": [target.dict() for target in result.targets]
            }, indent=2)
            
            # Create artifact with calculation engine data
            artifact = await self.artifact_service.create_artifact(
                db=db,
                artifact_data=ArtifactCreateSchema(
                    session_id=session_id,
                    title="Calculation Engine Result",
                    artifact_type=ArtifactType.ADVICE,
                    content=artifact_content,
                    artifact_metadata={
                        "source": "calc_engine",
                        "name_ids": name_ids,
                        "plant_id": plant_id,
                        "stage": "initial",
                        "calc_engine_data": {
                            "dependent_variables": [var.dict() for var in result.dependent_variables],
                            "independent_variables": [var.dict() for var in result.independent_variables],
                            "targets": [target.dict() for target in result.targets]
                        }
                    }
                ),
                user_id=user_id,
                auth_data={"user_id": user_id}
            )
            
            if not artifact:
                self.logger.error('Failed to create artifact')
                # Continue anyway, don't fail the whole request
            
            artifact_id = artifact.get("id") if artifact else None
            self.logger.success(f'Artifact created with ID: {artifact_id}')
            
            # Return response with session_id, artifact_id, and data
            return {
                "session_id": session_id,
                "artifact_id": artifact_id,
                "dependent_variables": [var.dict() for var in result.dependent_variables],
                "independent_variables": [var.dict() for var in result.independent_variables],
                "targets": [target.dict() for target in result.targets]
            }
            
        except Exception as e:
            self.logger.error(f'Error getting calc engine result with session: {e}')
            raise e
    
    async def _get_ai_response(self, context: Dict[str, Any], plant_id: str = None) -> Optional[Dict[str, Any]]:
        """Get response from AI service"""
        try:
            if not AI_AGENT_URL:
                raise ValueError("AI service URL is not configured")
            
            # Prepare headers
            headers = {"Content-Type": "application/json"}
            if plant_id:
                headers["Plant-Id"] = plant_id
            
            # 3 minutes timeout
            timeout = httpx.Timeout(1000.0)
            
            async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
                response = await client.post(
                    AI_AGENT_URL,
                    json=context,
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    error_detail = response.text
                    self.logger.error(f"AI service error response: {error_detail}")
                    raise ValueError(f"AI service returned status: {response.status_code}, error: {error_detail}")
                
        except Exception as e:
            self.logger.error(f'Failed to get AI response: {str(e)}')
            raise ValueError(str(e))
    
    async def send_manual_ai_request(
        self, 
        manual_request: ManualAiRequestSchema,
        db: AsyncSession,
        user_id: int,
        auth_data: Dict[str, Any],
        plant_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Send manual AI request with different question types. If session_id provided, use existing session and update artifact."""
        try:
            self.logger.info('Sending manual AI request')
            
            # Step 1: Prepare the request data
            ai_request_data = {
                "data": manual_request.data.dict() if hasattr(manual_request.data, 'dict') else manual_request.data,
                "question_type": manual_request.label.value,  # AI service expects "question_type" not "label"
            }
            
            # Convert data to proper format based on type
            if manual_request.label == QuestionType.EXPLORE:
                # For explore type, data should be a list of entities
                ai_request_data["data"] = [entity.dict() for entity in manual_request.data]
                
            elif manual_request.label == QuestionType.VIEW:
                # For view type, data should be TsQuerySchema dict
                ai_request_data["data"] = manual_request.data.dict()
                
            elif manual_request.label == QuestionType.ADVICE:
                # Check if it's the simple format (AdvisorSimpleRequestSchema)
                if isinstance(manual_request.data, AdvisorSimpleRequestSchema):
                    self.logger.info("🔄 Processing simple advisor request format")
                    
                    # Extract name_ids from targets
                    name_ids = [target.name_id for target in manual_request.data.targets]
                    self.logger.info(f"   📋 Extracted {len(name_ids)} name_ids from targets: {name_ids}")
                    
                    # Build complete recommendation schema with pairs and targets
                    calc_engine_schema = await build_recommendation_schema(name_ids, plant_id)
                    self.logger.info(f"   ✅ Built schema with {len(calc_engine_schema.pairs)} pairs")
                    
                    # Update pairs with modified_limits
                    if manual_request.data.modified_limits and calc_engine_schema.pairs:
                        self.logger.info(f"🔄 Updating pairs with modified_limits: {manual_request.data.modified_limits}")
                        updated_pairs = update_pairs(manual_request.data.modified_limits, calc_engine_schema.pairs)
                        calc_engine_schema.pairs = updated_pairs
                    
                    # Update targets with new_value (target_value)
                    for target in calc_engine_schema.targets:
                        for target_update in manual_request.data.targets:
                            if target.name_id == target_update.name_id:
                                target.target_value = target_update.new_value
                                self.logger.info(f"   ✅ Updated target {target.name_id}: target_value = {target.target_value}")
                    
                    # Use the built schema
                    ai_request_data["data"] = calc_engine_schema.dict(by_alias=True)
                    
                else:
                    # Original format: RecommendationCalculationEngineSchema
                    # If modified_limits are provided, update the pairs before sending to AI
                    if manual_request.modified_limits and manual_request.data.pairs:
                        self.logger.info(f"🔄 Updating pairs with modified_limits: {manual_request.modified_limits}")
                        updated_pairs = update_pairs(manual_request.modified_limits, manual_request.data.pairs)
                        manual_request.data.pairs = updated_pairs
                    
                    ai_request_data["data"] = manual_request.data.dict(by_alias=True)
            
            # Step 2: Call the AI service first
            starttime = datetime.now()
            ai_response = await self._get_ai_response(ai_request_data, plant_id)
            execution_time = (datetime.now() - starttime).total_seconds()
            
            # Step 3: Only create/update session and message if AI responds successfully
            if ai_response:
                try:
                    # Check if session_id is provided in request
                    if manual_request.session_id:
                        # Use existing session
                        session_id = manual_request.session_id
                        self.logger.info(f'Using existing session: {session_id}')
                        
                        # Verify session exists and user has access
                        existing_session = await get_chat_session(db, session_id)
                        if not existing_session or existing_session.user_id != user_id:
                            self.logger.error(f'Session {session_id} not found or access denied')
                            raise ValueError("Session not found or access denied")
                    else:
                        # Create a new chat session
                        session_id = str(uuid.uuid4())
                        created_session = await create_chat_session(db, session_id, user_id)
                        if not created_session:
                            self.logger.error('Failed to create session')
                            raise ValueError("Failed to create session")
                        
                        self.logger.success(f'Session created: {session_id}')
                    
                    # Create a dummy message in the session
                    dummy_message = f"Manual AI request: {manual_request.label.value}"
                    
                    # Create chat message record
                    json_response = json.dumps(ai_response)
                    chat_message = await create_chat_message(
                        db=db,
                        session_id=session_id,
                        user_id=user_id,
                        message=dummy_message,
                        execution_time=execution_time,
                        response=json_response,
                        query="Manual AI request - direct response from AI service"
                    )
                    
                    # Create or update artifacts from AI response
                    created_artifacts = []
                    try:
                        # If session_id was provided, try to update existing artifact
                        if manual_request.session_id:
                            # Get existing artifacts from session
                            from queries.artifact_queries import get_artifacts_by_session
                            existing_artifacts = await get_artifacts_by_session(db, session_id, user_id, skip=0, limit=1)
                            
                            if existing_artifacts and len(existing_artifacts) > 0:
                                # Update the first artifact with AI response data in metadata
                                existing_artifact = existing_artifacts[0]
                                self.logger.info(f'Updating existing artifact {existing_artifact.id} with advisor_simulated_data')
                                
                                # Update artifact with AI answer as content and advisor_simulated_data in metadata
                                from queries.artifact_queries import update_artifact
                                
                                # Extract the answer from AI response
                                ai_answer = ai_response.get("answer", "") if isinstance(ai_response, dict) else str(ai_response)
                                
                                # Preserve existing metadata and add advisor_simulated_data
                                updated_metadata = existing_artifact.artifact_metadata or {}
                                updated_metadata.update({
                                    "stage": "completed",
                                    "advisor_simulated_data": ai_response
                                })
                                
                                updated_artifact = await update_artifact(
                                    db=db,
                                    artifact_id=existing_artifact.id,
                                    user_id=user_id,
                                    content=ai_answer,
                                    artifact_metadata=updated_metadata,
                                    message_id=chat_message.get('id') if chat_message and isinstance(chat_message, dict) else existing_artifact.message_id
                                )
                                
                                if updated_artifact:
                                    created_artifacts.append(self.artifact_service._format_artifact_response(updated_artifact))
                                    self.logger.success(f'Updated artifact {existing_artifact.id} with advisor_simulated_data')
                        
                        # If no artifact was updated, create new ones from AI response
                        if not created_artifacts:
                            for ai_item in ai_response:
                                artifact = await self.artifact_service.create_artifact_from_ai_response(
                                    db=db,
                                    session_id=session_id,
                                    user_id=user_id,
                                    ai_response=ai_item,
                                    message_id=chat_message.get('id') if chat_message and isinstance(chat_message, dict) else None
                                )
                                if artifact:
                                    created_artifacts.append(artifact)
                                    self.logger.info(f"Created artifact: {artifact.get('title', 'Untitled')}")
                    except Exception as artifact_error:
                        self.logger.warning(f"Failed to create/update artifacts: {artifact_error}")
                        # Don't fail the main response if artifact creation fails
                    
                    # Prepare response with session info and artifacts
                    response = {
                        "session_id": session_id,
                        "message": dummy_message,
                        "response": ai_response,
                        "artifacts": created_artifacts,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    self.logger.success('Successfully sent manual AI request and received response')
                    return response
                    
                except Exception as e:
                    self.logger.error(f'Error processing AI response: {e}')
                    error_response = {
                        "response": [],
                        "artifacts": [],
                        "timestamp": datetime.now().isoformat(),
                        "error": {
                            "type": "response_processing_error",
                            "message": "Failed to process AI response. Please try a different question."
                        }
                    }
                    return error_response
            else:
                # No AI response - don't create session
                error_response = {
                    "response": [],
                    "artifacts": [],
                    "timestamp": datetime.now().isoformat(),
                    "error": {
                        "type": "invalid_response",
                        "message": "Unable to generate a valid response for your question. Please try rephrasing it."
                    }
                }
                return error_response
            
        except Exception as e:
            self.logger.error(f'Error sending manual AI request: {e}')
            raise e