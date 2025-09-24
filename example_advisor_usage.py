"""
Example usage of the Advisor Service

This file demonstrates how to use the advisor service that was created.
The advisor service processes requests with tag_id, target_value, and unit_of_measure,
and returns an object with variables containing lists of tags.
"""

from services.advisor_services import AdvisorService
from schemas.schema import AdvisorRequestSchema
from sqlalchemy.ext.asyncio import AsyncSession

async def example_advisor_usage(db: AsyncSession):
    """
    Example of how to use the advisor service
    """
    # Initialize the advisor service
    advisor_service = AdvisorService()
    
    # Create a request with the required data
    request_data = AdvisorRequestSchema(
        tag_id="TAG_001",
        target_value=75.5,
        unit_of_measure="Celsius"
    )
    
    # Validate the request
    is_valid = await advisor_service.validate_request(request_data)
    if not is_valid:
        print("Request validation failed")
        return
    
    # Process the advisor request
    try:
        response = await advisor_service.process_advisor_request(db, request_data)
        
        if response:
            print("Advisor response received:")
            print(f"Number of variables: {len(response.variables)}")
            
            for variable_name, tag_list in response.variables.items():
                print(f"{variable_name}: {tag_list}")
        else:
            print("No response received from advisor service")
            
    except Exception as e:
        print(f"Error processing advisor request: {e}")

# Example of the expected response structure:
"""
The advisor service will return an AdvisorResponseSchema with this structure:

{
    "variables": {
        "variable1": ["tag_001", "tag_002", "tag_003"],
        "variable2": ["tag_004", "tag_005"],
        "variable3": ["tag_006", "tag_007", "tag_008", "tag_009"],
        "recommendations": ["tag_010", "tag_011"],
        "warnings": ["tag_012"]
    }
}

Each variable contains a list of tag IDs that are relevant to that category.
The exact variables and their contents will depend on your external function implementation.
"""
