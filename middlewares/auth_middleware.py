import jwt #type: ignore 
from fastapi import HTTPException, Security, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import dotenv
from utils.log import setup_logger
from typing import Optional, Dict, Any
from utils.response import fail_response

logger = setup_logger(__name__)

dotenv.load_dotenv('.env', override=True)

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

# Do not crash the app at import time; log and handle at request time instead
if not JWT_SECRET or not JWT_ALGORITHM:
    logger.error("JWT_SECRET or JWT_ALGORITHM environment variables not set")

security = HTTPBearer()

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify JWT token and return payload.
    Raises HTTPException if token is invalid.
    """
    try:
        # Guard against missing configuration at runtime
        if not JWT_SECRET or not JWT_ALGORITHM:
            logger.error("JWT configuration is missing at runtime")
            raise HTTPException(status_code=500, detail="Authentication is not configured on the server")
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Validate payload structure
        if "user_id" not in payload:
            logger.warning(f"Token missing user_id in payload: {payload}")
            return fail_response(f"Token missing user_id in payload: {payload}")
            # raise HTTPException(status_code=401, detail="Invalid token structure: missing user_id")]
            
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return fail_response('Token has expired')
        # raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication error")
    
async def authenticate_user(token: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """
    FastAPI dependency to authenticate a user from an HTTP request with a Bearer token.
    Returns the JWT payload containing user information.
    """
    payload = verify_token(token.credentials)
    logger.info(f"User authenticated: {payload.get('user_id')}")
    return payload

async def verify_ws_token(token: str) -> Dict[str, Any]:
    """
    Verify a JWT token from a WebSocket connection.
    Returns the JWT payload containing user information.
    Raises exceptions for invalid tokens - these should be caught by the caller.
    """
    return verify_token(token)

# Helper function to get user_id from authenticated user payload
def get_user_id(auth_data: Dict[str, Any]) -> int:
    """Extract user_id from authenticated user data"""
    return auth_data.get("user_id")

# Helper function to check if user has admin role
def is_admin(auth_data: Dict[str, Any]) -> bool:
    """Check if user has admin role"""
    roles = auth_data.get("roles", [])
    return "admin" in roles








