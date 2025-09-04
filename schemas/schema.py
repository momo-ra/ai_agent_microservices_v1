from pydantic import BaseModel, Field
from enum import Enum
from typing import List, TypeVar, Optional, Generic

T = TypeVar('T')

class ResponseModel(BaseModel, Generic[T]):
    """Generic response model for API responses"""
    status: str = Field(..., description="Status of the response, could be 'success' or 'fail'")
    data: Optional[T] = Field(None, description="Data returned in the response")
    message: Optional[str] = Field(None, description="Message accompanying the response")
    status_code: int = Field(..., description="HTTP status code of the response")

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

class QuestionType(str, Enum):
    """Enum for the type of the user's question"""
    ADVICE = "advice"
    VIEW = "view"
    EXPLORE = "explore"

class AiDataResponseSchema(BaseModel):
    name: str = Field(..., description="Name of the data")
    data: List[dict] = Field(..., description="Data points")

# be aware that the ai responses with List of this schema.
class AiResponseSchema(BaseModel):
    answer: str = Field(..., description="Answer provided by the AI")
    data: Optional[List[AiDataResponseSchema]] = Field(None, description="Additional data related to the answer")
    answer_type: Optional[AnswerType] = Field(..., description="Type of the answer")
    plot_type: Optional[PlotType] = Field(None, description="Type of plot if applicable")
    question_type: Optional[QuestionType] = Field(None, description="The type of question: advice, view, or explore")


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
    session_id: str