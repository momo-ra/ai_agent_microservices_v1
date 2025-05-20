from typing import Any, Dict, Optional
from schemas.schema import ResponseModel


def success_response(data:Any = None, message:Optional[str] = None) -> ResponseModel:
    return ResponseModel(status=True, message=message, data=data)

def fail_response(message:Optional[str] = None, status_code:int = 400) -> ResponseModel:
    return ResponseModel(status=False, message=message, data=None)