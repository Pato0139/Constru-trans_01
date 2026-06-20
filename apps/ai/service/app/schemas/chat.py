from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class HistoryMessage(BaseModel):
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message")
    session_id: Optional[str] = Field(None, description="Session ID for continuity")
    user_id: Optional[str] = Field(None, description="User ID")
    user_name: Optional[str] = Field(None, description="User name")
    user_role: Optional[str] = Field(None, description="User role")
    business_context: Dict[str, Any] = Field(default_factory=dict, description="Business context data")
    history: List[HistoryMessage] = Field(default_factory=list, description="Conversation history")
    use_rag: bool = Field(default=True, description="Whether to use RAG")


class ChatResponse(BaseModel):
    response: str = Field(..., description="AI response")
    session_id: str = Field(..., description="Session ID")
    model_used: Optional[str] = Field(None, description="Model used")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tools called")
    status: str = Field("ok", description="Response status")


class Message(BaseModel):
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


class ConversationSummary(BaseModel):
    conversation_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int
