from sqlalchemy.ext.asyncio import AsyncSession
from utils.log import setup_logger
from queries.advisor_queries import get_advisor_data, get_related_tags
from schemas.schema import (
    AdvisorRequestSchema, AdvisorResponseSchema, AdvisorNameIdsRequestSchema,
    AdvisorCalcEngineResultSchema, AdvisorCalcRequestWithTargetsSchema, AdvisorSimpleRequestSchema
)
from services.calculation_engine_services import build_execute_recommendation_query, finish_calc_engine_request
from typing import Dict, Any, Optional, List, Tuple
import json
import httpx
from dotenv import load_dotenv
import os

load_dotenv('.env', override=True)

AI_AGENT_URL = "http://38.128.233.128:8000/ai-agent/chat"

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
    
    async def send_to_ai(
        self, 
        simple_request: AdvisorSimpleRequestSchema,
        plant_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send calculation request with target values to AI.
        Builds RecommendationCalculationEngineSchema automatically from name_ids.
        
        Args:
            simple_request: Request containing name_ids and target_values
            plant_id: Plant ID for the request
        
        Returns:
            Response from AI service
        """
        try:
            self.logger.info('Sending calc request with targets to AI')
            
            print("🔧 BUILDING CALCULATION ENGINE REQUEST")
            print(f"   - name_ids: {simple_request.name_ids}")
            print(f"   - plant_id: {plant_id}")
            
            # Build the calculation engine request from name_ids
            calc_engine_result = await build_execute_recommendation_query(
                simple_request.name_ids, plant_id
            )
            
            if calc_engine_result and len(calc_engine_result) == 3:
                targets, dependent_variables, independent_variables = calc_engine_result
            else:
                print("❌ Invalid result from build_execute_recommendation_query")
                targets, dependent_variables, independent_variables = [], [], []
            
            print(f"📊 CALCULATION ENGINE RESULTS:")
            print(f"   - targets count: {len(targets)}")
            print(f"   - dependent_variables count: {len(dependent_variables)}")
            print(f"   - independent_variables count: {len(independent_variables)}")
            
            # Print targets details
            print("🎯 TARGETS:")
            for target in targets:
                print(f"   - {target.name_id}: current={target.current_value}, unit={target.unit_of_measurement}")
            
            # Print dependent variables
            print("📈 DEPENDENT VARIABLES:")
            if dependent_variables:
                for dep_var in dependent_variables:
                    print(f"   - {dep_var.name_id}: current={dep_var.current_value}, unit={dep_var.unit_of_measurement}")
            else:
                print("   - No dependent variables found")
            
            # Print independent variables
            print("📉 INDEPENDENT VARIABLES:")
            if independent_variables:
                for ind_var in independent_variables:
                    print(f"   - {ind_var.name_id}: current={ind_var.current_value}, unit={ind_var.unit_of_measurement}")
            else:
                print("   - No independent variables found")
            
            # Create the RecommendationCalculationEngineSchema
            from schemas.schema import RecommendationCalculationEngineSchema, RecommendationCalculationEnginePairSchema
            
            # Build pairs from dependent and independent variables
            pairs = []
            print("🔗 BUILDING PAIRS:")
            if dependent_variables and independent_variables:
                for dep_var in dependent_variables:
                    for ind_var in independent_variables:
                        # Create relationship and pair
                        relationship = {
                            "type": "affects",
                            "gain": 1.0,  # Default gain, should be calculated based on actual data
                            "gain_unit": None
                        }
                        
                        # Create the pair data in the correct format
                        pair_data = {
                            "relationship": relationship,
                            "from": ind_var.dict(),
                            "to": dep_var.dict()
                        }
                        
                        pair = RecommendationCalculationEnginePairSchema(**pair_data)
                        pairs.append(pair)
                        print(f"   - {ind_var.name_id} -> {dep_var.name_id} (gain: {relationship['gain']})")
            else:
                print("   - No pairs to create (missing dependent or independent variables)")
            
            print(f"   - Total pairs created: {len(pairs)}")
            
            # Create the full calculation request
            calc_request = RecommendationCalculationEngineSchema(
                pairs=pairs,
                targets=targets,
                label="recommendations"
            )
            
            print("✅ CALCULATION REQUEST CREATED:")
            print(f"   - pairs: {len(calc_request.pairs)}")
            print(f"   - targets: {len(calc_request.targets)}")
            print(f"   - label: {calc_request.label}")
            
            # Finish the calc engine request with target values
            print("🎯 APPLYING TARGET VALUES:")
            for name_id, target_value in simple_request.target_values.items():
                print(f"   - {name_id}: {target_value}")
            
            finish_calc_engine_request(
                simple_request.target_values,
                calc_request
            )
            
            # Prepare the request data for AI service
            ai_request_data = {
                "calc_request": calc_request.dict(),
                "target_values": simple_request.target_values
            }
            
            print("📤 FINAL AI REQUEST DATA:")
            print("=" * 60)
            print("CALC_REQUEST:")
            print(f"   - pairs: {len(ai_request_data['calc_request']['pairs'])}")
            print(f"   - targets: {len(ai_request_data['calc_request']['targets'])}")
            print(f"   - label: {ai_request_data['calc_request']['label']}")
            print("TARGET_VALUES:")
            for k, v in ai_request_data['target_values'].items():
                print(f"   - {k}: {v}")
            print("=" * 60)
            
            # Print the complete JSON that will be sent to AI
            print("🎯 COMPLETE JSON TO BE SENT TO AI:")
            print("=" * 80)
            import json
            print(json.dumps(ai_request_data, indent=2, default=str))
            print("=" * 80)
            
            # Call the AI service
            ai_response = await self._get_ai_response(ai_request_data, plant_id)
            
            self.logger.success('Successfully sent request to AI and received response')
            return ai_response
            
        except Exception as e:
            self.logger.error(f'Error sending to AI: {e}')
            raise e
    
    async def _get_ai_response(self, context: Dict[str, Any], plant_id: str = None) -> Optional[Dict[str, Any]]:
        """Get response from AI service"""
        try:
            print("🤖 CALLING AI SERVICE")
            print(f"   - AI_AGENT_URL: {AI_AGENT_URL}")
            print(f"   - plant_id: {plant_id}")
            
            self.logger.info(f'AI_AGENT_URL = {AI_AGENT_URL}')
            
            if not AI_AGENT_URL:
                self.logger.error('AI_AGENT_URL is not set!')
                raise ValueError("AI service URL is not configured")
            
            # 3 minutes timeout
            timeout = httpx.Timeout(1000.0)
            
            self.logger.info('Starting AI request - this may take around 1 minute...')
            
            # Prepare headers
            headers = {"Content-Type": "application/json"}
            if plant_id:
                headers["Plant-Id"] = plant_id
                self.logger.info(f'Sending Plant-Id header: {plant_id}')
            else:
                self.logger.warning('No plant_id provided for AI request')
            
            print("📡 REQUEST HEADERS:")
            for key, value in headers.items():
                print(f"   - {key}: {value}")
            
            print("📦 REQUEST BODY (JSON):")
            print("=" * 60)
            import json
            print(json.dumps(context, indent=2, default=str))
            print("=" * 60)
            
            async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
                print("🚀 SENDING REQUEST TO AI SERVICE...")
                response = await client.post(
                    AI_AGENT_URL,
                    json=context,
                    headers=headers
                )
                
                print(f"📨 AI SERVICE RESPONSE:")
                print(f"   - Status Code: {response.status_code}")
                print(f"   - Headers: {dict(response.headers)}")
                
                self.logger.info(f'Response status: {response.status_code}')
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        print("✅ SUCCESSFUL AI RESPONSE:")
                        print("=" * 60)
                        print(json.dumps(response_data, indent=2, default=str))
                        print("=" * 60)
                        self.logger.success('Received JSON response from AI!')
                        return response_data
                    except Exception as json_error:
                        print(f"❌ JSON PARSING ERROR: {json_error}")
                        print(f"Raw response text: {response.text[:500]}...")
                        self.logger.error(f'Error parsing JSON response: {json_error}')
                        raise ValueError(f"Failed to parse AI service response: {str(json_error)}")
                else:
                    print(f"❌ AI SERVICE ERROR:")
                    print(f"   - Status: {response.status_code}")
                    print(f"   - Response: {response.text[:500]}...")
                    self.logger.error(f'Error from AI service: Status {response.status_code}, Response: {response.text[:200]}')
                    raise ValueError(f"AI service returned status: {response.status_code}")
                
            raise ValueError("Failed to get a valid response from the AI service")
                
        except Exception as e:
            print(f"💥 EXCEPTION IN AI SERVICE CALL: {str(e)}")
            self.logger.error(f'Failed to get AI response: {str(e)}')
            raise ValueError(str(e))
