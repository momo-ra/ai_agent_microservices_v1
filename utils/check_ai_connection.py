# utils/connection_test.py
import httpx
import asyncio
import os
from utils.log import setup_logger

logger = setup_logger("connection_test")

async def test_ai_connection(url=None):
    """أداة لتشخيص الاتصال بخدمة الذكاء الاصطناعي"""
    if not url:
        url = os.getenv("AI_AGENT_URL")
        
    if not url:
        logger.error("AI_AGENT_URL is not set in environment variables")
        return False
        
    logger.info(f"Testing connection to: {url}")
    
    # اختبار صحة عنوان URL
    if not url.startswith(("http://", "https://")):
        logger.error(f"Invalid URL: {url} - URL must start with http:// or https://")
        return False
    
    # اختبار اتصال GET
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            logger.info("Trying GET request...")
            get_response = await client.get(url)
            logger.info(f"GET response: {get_response.status_code}")
            
            # اختبار اتصال POST
            test_payload = {"input": "Test connection"}
            logger.info("Trying POST request with test payload...")
            post_response = await client.post(url, json=test_payload)
            logger.info(f"POST response: {post_response.status_code}")
            
            # عرض محتوى الرد
            content_preview = post_response.text[:200] if post_response.text else "Empty response"
            logger.info(f"Response preview: {content_preview}")
            
            # التحقق من صحة JSON
            try:
                json_response = post_response.json()
                logger.info(f"Valid JSON response: {json_response}")
                return True
            except Exception as json_err:
                logger.error(f"Invalid JSON response: {json_err}")
                return False
                
    except httpx.HTTPStatusError as status_err:
        logger.error(f"HTTP status error: {status_err}")
    except httpx.RequestError as req_err:
        logger.error(f"Request error: {req_err}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        
    return False