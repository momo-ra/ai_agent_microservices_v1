from pydantic import BaseModel, Field
from enum import Enum
from typing import List, TypeVar, Optional, Generic, Dict, Any

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


class AiDataResponseSchema(BaseModel):
    name: str = Field(..., description="Name of the data")
    data: List[dict] = Field(..., description="Data points")

class QuestionType(str, Enum):
    """Enum for the type of the user's question"""
    ADVICE = "advice"
    VIEW = "view"
    EXPLORE = "explore"


# be aware that the ai responses with List of this schema.
class AiResponseSchema(BaseModel):
    answer: str = Field(..., description="Answer provided by the AI")
    data: Optional[List[AiDataResponseSchema]] = Field(None, description="Additional data related to the answer")
    answer_type: Optional[AnswerType] = Field(..., description="Type of the answer")
    plot_type: Optional[PlotType] = Field(None, description="Type of plot if applicable")
    question_type: Optional[QuestionType] = Field(None, description="The type of question: advice, view, or explore")
    rewritten_question: str = Field(..., description="The rewritten question by the AI")


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
    input_message: str
    session_id: str

class ArtifactType(str, Enum):
    """Enum for artifact types - based on AI response types"""
    # Based on answer_type
    ANSWER = "answer"
    AI_FEEDBACK = "ai_feedback"
    
    # Based on plot_type
    BAR_PLOT = "bar_plot"
    LINE_PLOT = "line_plot"
    SCATTER_PLOT = "scatter_plot"
    HISTOGRAM_PLOT = "histogram_plot"
    PIE_PLOT = "pie_plot"
    
    # Based on question_type
    ADVICE = "advice"
    VIEW = "view"
    EXPLORE = "explore"
    
    # Content-based detection
    CODE = "code"
    DIAGRAM = "diagram"
    DATA = "data"
    DOCUMENT = "document"
    GENERAL = "general"

class ArtifactCreateSchema(BaseModel):
    """Schema for creating a new artifact"""
    session_id: str = Field(..., description="Session ID this artifact belongs to")
    title: str = Field(..., description="Title of the artifact")
    artifact_type: ArtifactType = Field(default=ArtifactType.GENERAL, description="Type of artifact")
    content: str = Field(..., description="Content of the artifact")
    artifact_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    message_id: Optional[int] = Field(None, description="ID of the message that generated this artifact")

class ArtifactResponseSchema(BaseModel):
    """Schema for artifact response"""
    id: int
    session_id: str
    user_id: int
    title: str
    artifact_type: str
    content: str
    artifact_metadata: Optional[Dict[str, Any]]
    is_active: bool
    message_id: Optional[int]
    created_at: str
    updated_at: str

class ArtifactUpdateSchema(BaseModel):
    """Schema for updating an artifact"""
    title: Optional[str] = Field(None, description="Updated title")
    content: Optional[str] = Field(None, description="Updated content")
    artifact_metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    is_active: Optional[bool] = Field(None, description="Active status")

class ArtifactListResponseSchema(BaseModel):
    """Schema for listing artifacts"""
    artifacts: List[ArtifactResponseSchema]
    total_count: int
    session_id: str

# =============================================================================
# CHAT SESSION SCHEMAS
# =============================================================================

class ChatSessionResponseSchema(BaseModel):
    """Schema for chat session response"""
    id: int
    session_id: str
    user_id: int
    user_name: Optional[str]
    chat_name: Optional[str]
    is_starred: bool
    created_at: str
    updated_at: str
    message_count: Optional[int] = 0
    last_message: Optional[str] = None
    last_message_time: Optional[str] = None

class ChatSessionListResponseSchema(BaseModel):
    """Schema for listing chat sessions"""
    sessions: List[ChatSessionResponseSchema]
    total_count: int
    skip: int
    limit: int

class ChatSessionUpdateSchema(BaseModel):
    """Schema for updating a chat session"""
    chat_name: Optional[str] = Field(None, description="Updated chat name")
    is_starred: Optional[bool] = Field(None, description="Starred status")

class ChatMessageUpdateSchema(BaseModel):
    """Schema for updating a chat message"""
    message: str = Field(..., description="Updated message content")

class ChatSearchRequestSchema(BaseModel):
    """Schema for chat search request"""
    search_term: str = Field(..., description="Search term for chat names")
    skip: int = Field(0, description="Number of results to skip")
    limit: int = Field(100, description="Maximum number of results to return")

class RecentChatsRequestSchema(BaseModel):
    """Schema for recent chats request"""
    days: int = Field(7, description="Number of days to look back")
    skip: int = Field(0, description="Number of results to skip")
    limit: int = Field(100, description="Maximum number of results to return")

# =============================================================================
# ADVISOR SERVICE SCHEMAS
# =============================================================================

class AdvisorRequestSchema(BaseModel):
    """Schema for advisor service request"""
    tag_id: str = Field(..., description="ID of the tag to analyze")
    target_value: float = Field(..., description="Target value for the tag")
    unit_of_measure: str = Field(..., description="Unit of measure for the target value")

class TagListSchema(BaseModel):
    """Schema for a list of tags"""
    tags: List[str] = Field(..., description="List of tag IDs")

class AdvisorResponseSchema(BaseModel):
    """Schema for advisor service response - object with variables containing lists of tags"""
    # This will be a dynamic object where each variable is a list of tags
    # The exact structure will depend on the external function response
    variables: Dict[str, List[str]] = Field(..., description="Object containing variables, each with a list of tag IDs")