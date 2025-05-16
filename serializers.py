import json
from typing import List, Dict, Any
from utils.log import setup_logger
from datetime import datetime

logger = setup_logger(__name__)

def format_api_response(session_id: str, message: str, raw_data: Any) -> Dict[str, Any]:
    response_data = []
    if isinstance(raw_data, list):
        # If raw_data is already a list of tuples from query
        for row in raw_data:
            if len(row) >= 3:  # timestamp, value, tag_id
                try:
                    timestamp = row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0])
                    value = float(row[1]) if row[1] is not None else 0.0
                    tag_id = str(row[2]) if row[2] is not None else ""
                    response_data.append((timestamp, value, tag_id))
                except Exception as e:
                    logger.error(f"Error processing row: {e}")
    
    # Group by tag_id
    tag_groups = {}
    for timestamp, value, tag_id in response_data:
        if tag_id not in tag_groups:
            tag_groups[tag_id] = []
        
        tag_groups[tag_id].append({
            "timestamp": timestamp,
            "value": value
        })
    
    # Format response
    formatted_response = [
        {
            "tag_id": tag_id,
            "data": data_points
        }
        for tag_id, data_points in tag_groups.items()
    ]
    
    # Create full response
    return {
        "session_id": session_id,
        "message": message,
        "response": formatted_response,
        "timestamp": datetime.now().isoformat()
    }

def format_history_response(chat_message) -> Dict[str, Any]:
    """
    Format a history message into the API response structure
    
    Args:
        chat_message: ChatMessage object from database
        
    Returns:
        Formatted API response
    """
    try:
        # Parse response if it exists
        response_data = []
        if chat_message.response:
            try:
                parsed_response = json.loads(chat_message.response)
                
                # Check if response is already in the new format (with tag_id and data)
                if isinstance(parsed_response, list) and len(parsed_response) > 0 and isinstance(parsed_response[0], dict):
                    if "tag_id" in parsed_response[0] and "data" in parsed_response[0]:
                        # Already in correct format
                        response_data = parsed_response
                    else:
                        # Convert old format (flat) to new format (grouped by tag)
                        tag_groups = {}
                        
                        for item in parsed_response:
                            if not isinstance(item, dict):
                                continue
                                
                            # Extract fields
                            if "tag_id" in item and "timestamp" in item and "value" in item:
                                tag_id = item["tag_id"]
                                
                                if tag_id not in tag_groups:
                                    tag_groups[tag_id] = []
                                    
                                tag_groups[tag_id].append({
                                    "timestamp": item["timestamp"],
                                    "value": float(item["value"])
                                })
                        
                        # Format response
                        response_data = [
                            {
                                "tag_id": tag_id,
                                "data": data_points
                            }
                            for tag_id, data_points in tag_groups.items()
                        ]
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON for message {chat_message.id}")
                response_data = []
            except Exception as e:
                logger.error(f"Error formatting history response: {e}")
                response_data = []
        
        # Create full response
        response = {
            "session_id": chat_message.session_id,
            "message": chat_message.message,
            "response": response_data,
            "timestamp": chat_message.created_at.isoformat() if hasattr(chat_message.created_at, 'isoformat') else str(chat_message.created_at)
        }
        
        # If there's an error stored in the query field (our workaround)
        if chat_message.query and chat_message.query.startswith("Error:"):
            response["error"] = {
                "type": "service_error",
                "message": chat_message.query[7:].strip()  # Remove "Error: " prefix
            }
            
        return response
    except Exception as e:
        logger.error(f"Error in format_history_response: {e}")
        # Return a minimal valid response on error
        return {
            "session_id": chat_message.session_id if hasattr(chat_message, "session_id") else "",
            "message": chat_message.message if hasattr(chat_message, "message") else "",
            "response": [],
            "timestamp": chat_message.created_at.isoformat() if hasattr(chat_message, "created_at") and hasattr(chat_message.created_at, "isoformat") else ""
        }