from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse
from schemas.schema import ResponseModel


def success_response(data:Any = None, message:Optional[str] = None, status_code:int = 200) -> JSONResponse:
    response = ResponseModel(status="success", message=message, data=data, status_code=status_code)
    return JSONResponse(content=response.dict(), status_code=status_code)

def fail_response(message:Optional[str] = None, status_code:int = 400) -> JSONResponse:
    response = ResponseModel(status="fail", message=message, data=None, status_code=status_code)
    return JSONResponse(content=response.dict(), status_code=status_code)


