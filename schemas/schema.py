from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
from typing import List, TypeVar, Optional, Generic, Dict, Any, Literal, Union

T = TypeVar('T')

class ResponseModel(BaseModel, Generic[T]):
    """Generic response model for API responses"""
    status: str = Field(..., description="Status of the response, could be 'success' or 'fail'")
    data: Optional[T] = Field(None, description="Data returned in the response")
    message: Optional[str] = Field(None, description="Message accompanying the response")
    status_code: int = Field(..., description="HTTP status code of the response")

class PaginatedResponseData(BaseModel, Generic[T]):
    """Generic paginated data wrapper"""
    items: List[T] = Field(..., description="List of items in current page")
    total: int = Field(..., description="Total number of items across all pages")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum items per page")
    has_more: bool = Field(..., description="Whether there are more items available")
    page: int = Field(..., description="Current page number (1-indexed)")
    total_pages: int = Field(..., description="Total number of pages")

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


class RecommendationLimitEntitySchema(RecommendationEntitySchema):
    priority: Optional[str]=None
    parameter_source: Optional[str] = Field(None, alias="source")

class RecommendationElementSchema(RecommendationEntitySchema):
    slack_weight: Optional[RecommendationEntitySchema] =None
    mv_weight: Optional[RecommendationEntitySchema]=None
    low_limits: Optional[List[RecommendationLimitEntitySchema]]=None
    high_limits: Optional[List[RecommendationLimitEntitySchema]]=None
    variable_type: Optional[str] = None
    unitary_price: Optional[RecommendationEntitySchema] = None
    target_value: Optional[float] = None
    timestamp: Optional[str] = None

    @field_validator("low_limits",mode="before")
    @staticmethod
    def validate_low_limits(low_limits:Optional[List[Dict]]=None)->Optional[List[RecommendationLimitEntitySchema]]:
        if low_limits is None:
            return None
        if isinstance(low_limits, list) and isinstance(low_limits[0], RecommendationLimitEntitySchema):
            return low_limits
        new_low_limits = []
        for limit in low_limits:
            if limit["name_id"] is not None:
                new_low_limits.append(limit)
        if new_low_limits == []:
            return None
        return new_low_limits
    @field_validator("high_limits",mode="before")
    @staticmethod
    def validate_high_limits(high_limits:Optional[List[Dict]]=None)->Optional[List[RecommendationLimitEntitySchema]]:
        if high_limits is None:
            return None
        if isinstance(high_limits, list) and isinstance(high_limits[0], RecommendationLimitEntitySchema):
            return high_limits
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
    model_config = {"populate_by_name": True}
    
    relationship: RecommendationRelationshipSchema
    from_: RecommendationElementSchema   = Field(...,alias="from")
    to_: RecommendationElementSchema = Field(...,alias="to")

class RecommendationCalculationEngineSchema(BaseModel):
    "schema of the input to the API call of the recommendation calculation engine"
    model_config = {"populate_by_name": True}
    
    pairs: List[RecommendationCalculationEnginePairSchema]
    targets: List[RecommendationElementSchema]
    label:str = Field(default="recommendations")

class AdvisorCompleteRequestSchema(BaseModel):
    """Complete schema for advisor request - frontend sends full calculation engine data"""
    dependent_variables: List[RecommendationElementSchema] = Field(..., description="Dependent variables from calculation engine")
    independent_variables: List[RecommendationElementSchema] = Field(..., description="Independent variables from calculation engine")
    targets: List[RecommendationElementSchema] = Field(..., description="Target variables from calculation engine")
    target_values: Dict[str, float] = Field(..., description="Target values for each variable")
    pairs: Optional[List[RecommendationCalculationEnginePairSchema]] = Field(None, description="Original pairs from Neo4j (relationships between variables)")

# =============================================================================
# ADVISOR ENDPOINT SCHEMAS
# =============================================================================

class AdvisorNameIdsRequestSchema(BaseModel):
    """Schema for advisor name_ids request"""
    name_ids: List[str] = Field(..., description="List of name IDs to analyze")

class AdvisorCalcEngineResultSchema(BaseModel):
    """Schema for advisor calculation engine result"""
    dependent_variables: List[RecommendationElementSchema] = Field(..., description="Dependent variables")
    independent_variables: List[RecommendationElementSchema] = Field(..., description="Independent variables")
    targets: List[RecommendationElementSchema] = Field(..., description="Targets")
    pairs: List[RecommendationCalculationEnginePairSchema] = Field(..., description="Original pairs from Neo4j with relationships")

class AdvisorCalcRequestWithTargetsSchema(BaseModel):
    """Schema for advisor calculation request with target values"""
    calc_request: RecommendationCalculationEngineSchema = Field(..., description="Calculation engine request")
    target_values: Dict[str, float] = Field(..., description="Target values for each variable")



class ManualAiRequestSchema(BaseModel):
    """Schema for manual AI requests with different question types"""
    model_config = {"populate_by_name": True}
    
    data: Union[List[EntitySchema], TsQuerySchema, RecommendationCalculationEngineSchema]
    label: QuestionType = Field(..., alias="question_type", description="Type of question to ask AI")
    
    @model_validator(mode="before")
    @classmethod
    def validate_data_based_on_question_type(cls, values):
        if isinstance(values, dict):
            question_type = values.get("question_type")
            data = values.get("data")
            
            if question_type == QuestionType.VIEW:
                if data and isinstance(data, dict):
                    values["data"] = TsQuerySchema(**data)
            elif question_type == QuestionType.EXPLORE:
                if data and isinstance(data, list):
                    values["data"] = [EntitySchema(**item) for item in data]
            elif question_type == QuestionType.ADVICE:
                if data and isinstance(data, dict):
                    values["data"] = RecommendationCalculationEngineSchema(**data)
        
        return values
