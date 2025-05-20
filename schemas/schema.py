from pydantic import BaseModel, Field
from enum import Enum
from typing import List, TypeVar, Optional, Generic
from datetime import datetime

T = TypeVar('T')

class ResponseModel(BaseModel, Generic[T]):
    """Generic response model for API responses"""
    status: bool = Field(..., description="Status of the response")
    data: Optional[T] = Field(None, description="Data returned in the response")
    message: Optional[str] = Field(None, description="Message accompanying the response")

class AnswerType(str, Enum):
    """Enum for possible answer types"""
    ANSWER = "Answer"
    AI_FEEDBACK = "Ai Feedback"

class PlotType(str, Enum):
    """Enum for possible plot types"""
    BAR = "bar_plot"
    LINE = "line_plot"
    SCATTER = "scatter_plot"
    HISTOGRAM = "histogram_plot"
    PIE = "pie_plot"

class AiDataResponseSchema(BaseModel):
    name: str = Field(..., description="Name of the data")
    data: List[dict] = Field(..., description="Data points")

# be aware that the ai responses with List of this schema.
class AiResponseSchema(BaseModel):
    answer: str = Field(..., description="Answer provided by the AI")
    data: Optional[List[AiDataResponseSchema]] = Field(None, description="Additional data related to the answer")
    answer_type: Optional[AnswerType] = Field(..., description="Type of the answer")
    plot_type: Optional[PlotType] = Field(None, description="Type of plot if applicable")




class DataPoint(BaseModel):
    """Individual data point with timestamp and value"""
    timestamp: str
    value: float

class TagData(BaseModel):
    """Group of data points for a specific tag"""
    tag_id: str
    data: List[DataPoint]

class MessageResponse(BaseModel):
    """API response format with nested structure"""
    session_id: str
    message: str
    response: List[TagData]
    timestamp: str

class MessageRequest(BaseModel):
    message: str