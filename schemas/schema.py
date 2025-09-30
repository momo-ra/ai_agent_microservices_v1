from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import List, TypeVar, Optional, Generic, Dict, Any, Literal, Union

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
    AI_FEEDBACK = "Ai feedback"
    ERROR = "Error"

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
    """Enum for question types"""
    EXPLORE = "explore"
    VIEW = "view"
    ADVICE = "advice"

class GroupingFunction(str, Enum):
    """Enum for grouping functions"""
    AVG = "AVG"
    SUM = "SUM"
    MIN = "MIN"
    MAX = "MAX"
    COUNT = "COUNT"
    FIRST = "FIRST"
    LAST = "LAST"

class EntitySchema(BaseModel):
    """Schema for retrieving an entity within the knowledgeGraph"""
    labels: List[str] = Field(..., min_length=1, description="The labels of the entity, Not nullable, Not empty")
    name_id: str = Field(..., min_length=1, description="The name_id of the entity, Not nullable, Not empty")

class TsQuerySchema(BaseModel):
    """Schema for time series queries"""
    start_date: str
    end_date: str
    name_ids: List[str]
    time_bucket: Optional[str] = None
    grouping_function: Optional[GroupingFunction] = None
    plot_type: Optional[PlotType] = None

class ShortcutQuestion(BaseModel):
    """Schema for shortcut questions to AI"""
    data: Union[List[EntitySchema], TsQuerySchema, 'RecommendationCalculationEngineSchema']
    label: QuestionType
    
    @field_validator("data", mode="after")
    @classmethod
    def validate_data(cls, v, info):
        label = info.data.get("label")
        if (label == QuestionType.VIEW and not isinstance(v, TsQuerySchema)) or \
           (label == QuestionType.EXPLORE and not isinstance(v, list)) or \
           (label == QuestionType.ADVICE and not isinstance(v, RecommendationCalculationEngineSchema)):
            raise ValueError(f"Invalid data type for {label}")
        return v

# be aware that the ai responses with List of this schema.
class AiResponseSchema(BaseModel):
    answer: str = Field(..., description="Answer provided by the AI")
    data: Optional[List[Union[str, Dict]]] = Field(None, description="Additional data related to the answer")
    answer_type: AnswerType = Field(..., description="Type of the answer")
    plot_type: Optional[PlotType] = Field(None, description="Type of plot if applicable")
    question_type: Optional[QuestionType] = Field(None, description="The type of question: advice, view, or explore")
    rewritten_question: str = Field(..., description="The rewritten question by the AI")
    advice_data: Optional['AdvisorCompleteRequestSchema'] = Field(None, description="Advice data when question_type is advice")

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


# =============================================================================
# CALCULATION ENGINE SCHEMAS
# =============================================================================

class RecommendationRelationshipSchema(BaseModel):
    type:Literal["affects","is_affected"]
    gain: float
    gain_unit: Optional[str] = None

class RecommendationEntitySchema(BaseModel):
    unit_of_measurement: Optional[str]=None
    name_id:str
    current_value: Optional[float]=None

class RecommendationTargetEntitySchema(RecommendationEntitySchema):
    target_value: Optional[float] = None
    time_stamp: Optional[str] = None

class RecommendationLimitEntitySchema(RecommendationEntitySchema):
    priority: Optional[str]=None
    parameter_source: Optional[str]=None

class RecommendationPairElemSchema(RecommendationEntitySchema):
    slack_weight: Optional[RecommendationEntitySchema] =None
    mv_weight: Optional[RecommendationEntitySchema]=None
    low_limits: Optional[List[RecommendationLimitEntitySchema]]=None
    high_limits: Optional[List[RecommendationLimitEntitySchema]]=None

    @field_validator("low_limits",mode="before")
    @staticmethod
    def validate_low_limits(low_limits:Optional[List[RecommendationLimitEntitySchema]])->Optional[List[RecommendationLimitEntitySchema]]:
        new_low_limits = []
        for limit in low_limits:
            if limit["name_id"] is not None:
                new_low_limits.append(limit)
        if new_low_limits == []:
            return None
        return new_low_limits
        
    @field_validator("high_limits",mode="before")
    @staticmethod
    def validate_high_limits(high_limits:Optional[List[RecommendationLimitEntitySchema]])->Optional[List[RecommendationLimitEntitySchema]]:
        new_high_limits = []
        for limit in high_limits:
            if limit["name_id"] is not None:
                new_high_limits.append(limit)
        if new_high_limits == []:
            return None
        return new_high_limits

class RecommendationCalculationEnginePairSchema(BaseModel):
    "schema of each Pair element, out from the neo4j query"
    "from is folloowed by _ because it's a reserved word"
    relationship: RecommendationRelationshipSchema
    from_: RecommendationPairElemSchema = Field(...,alias="from")
    to_: RecommendationPairElemSchema = Field(...,alias="to")

class RecommendationCalculationEngineSchema(BaseModel):
    "schema of the input to the API call of the recommendation calculation engine"
    pairs: List[RecommendationCalculationEnginePairSchema]
    targets: List[RecommendationTargetEntitySchema]
    # label: Literal["recommendations","what_if"]

class AdvisorCompleteRequestSchema(BaseModel):
    """Complete schema for advisor request - frontend sends full calculation engine data"""
    dependent_variables: List[RecommendationPairElemSchema] = Field(..., description="Dependent variables from calculation engine")
    independent_variables: List[RecommendationPairElemSchema] = Field(..., description="Independent variables from calculation engine")
    targets: List[RecommendationTargetEntitySchema] = Field(..., description="Target variables from calculation engine")
    target_values: Dict[str, float] = Field(..., description="Target values for each variable")

# =============================================================================
# ADVISOR ENDPOINT SCHEMAS
# =============================================================================

class AdvisorNameIdsRequestSchema(BaseModel):
    """Schema for advisor name_ids request"""
    name_ids: List[str] = Field(..., description="List of name IDs to analyze")

class AdvisorCalcEngineResultSchema(BaseModel):
    """Schema for advisor calculation engine result"""
    dependent_variables: List[RecommendationPairElemSchema] = Field(..., description="Dependent variables")
    independent_variables: List[RecommendationPairElemSchema] = Field(..., description="Independent variables")
    targets: List[RecommendationTargetEntitySchema] = Field(..., description="Targets")

class AdvisorCalcRequestWithTargetsSchema(BaseModel):
    """Schema for advisor calculation request with target values"""
    calc_request: RecommendationCalculationEngineSchema = Field(..., description="Calculation engine request")
    target_values: Dict[str, float] = Field(..., description="Target values for each variable")



class ManualAiRequestSchema(BaseModel):
    """Schema for manual AI requests with different question types"""
    question_type: QuestionType = Field(..., description="Type of question to ask AI")
    
    # For explore type - use EntitySchema
    entity_data: Optional[List[EntitySchema]] = Field(None, description="Entity data for explore type")
    
    # For view type - use TsQuerySchema
    ts_query_data: Optional[TsQuerySchema] = Field(None, description="Time series query data for view type")
    
    # For advice type - use the complete request schema
    advice_data: Optional[AdvisorCompleteRequestSchema] = Field(None, description="Advice data for advice type")
