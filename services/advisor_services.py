from sqlalchemy.ext.asyncio import AsyncSession
from utils.log import setup_logger
from queries.advisor_queries import get_advisor_data, get_related_tags
from schemas.schema import AdvisorRequestSchema, AdvisorResponseSchema
from typing import Dict, Any, Optional, List
import json

logger = setup_logger(__name__)

class AdvisorService:
    """Service for handling advisor-related operations"""
    
    def __init__(self):
        self.logger = logger
    
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
