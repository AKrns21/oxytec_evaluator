"""Pydantic schemas for API validation."""

from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


# Session Schemas
class SessionCreate(BaseModel):
    """Schema for creating a new session."""
    user_metadata: dict[str, Any] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    """Schema for session response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    user_metadata: Optional[dict[str, Any]] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class SessionStatus(BaseModel):
    """Schema for session status."""
    session_id: UUID
    status: str
    stream_url: str


# Document Schemas
class DocumentUpload(BaseModel):
    """Schema for uploaded document."""
    filename: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None


class DocumentResponse(BaseModel):
    """Schema for document response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    filename: str
    file_path: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    uploaded_at: datetime


# Agent Output Schemas
class AgentOutputResponse(BaseModel):
    """Schema for agent output."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: UUID
    agent_type: str
    agent_instance: Optional[str] = None
    output_type: Optional[str] = None
    content: dict[str, Any]
    tokens_used: Optional[int] = None
    duration_ms: Optional[int] = None
    created_at: datetime


# Log Schemas
class SessionLogResponse(BaseModel):
    """Schema for session log."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: UUID
    timestamp: datetime
    agent_type: str
    agent_instance: Optional[str] = None
    log_level: Optional[str] = None
    message: Optional[str] = None
    data: Optional[dict[str, Any]] = None


# Debug Schemas
class DebugInfoResponse(BaseModel):
    """Schema for debug information."""
    session_id: UUID
    logs: list[SessionLogResponse]
    agent_outputs: list[AgentOutputResponse]


# Product Schemas
class ProductCreate(BaseModel):
    """Schema for creating a product."""
    name: str
    category: Optional[str] = None
    technical_specs: dict[str, Any]
    description: Optional[str] = None


class ProductResponse(BaseModel):
    """Schema for product response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: Optional[str] = None
    technical_specs: dict[str, Any]
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Product Search Schemas
class ProductSearchResult(BaseModel):
    """Schema for product search result."""
    product_id: UUID
    product_name: str
    category: Optional[str] = None
    technical_specs: dict[str, Any]
    relevant_chunk: str
    metadata: Optional[dict[str, Any]] = None
    similarity: float


# SSE Event Schemas
class SSEEvent(BaseModel):
    """Schema for Server-Sent Events."""
    event: str
    data: dict[str, Any]


# Agent Graph State Schema (for reference)
class GraphStateSchema(BaseModel):
    """Schema representing the agent graph state."""
    session_id: UUID
    documents: list[dict[str, Any]] = Field(default_factory=list)
    user_input: dict[str, Any] = Field(default_factory=dict)
    extracted_facts: Optional[dict[str, Any]] = None
    planner_plan: Optional[dict[str, Any]] = None
    subagent_results: list[dict[str, Any]] = Field(default_factory=list)
    risk_assessment: Optional[dict[str, Any]] = None
    final_report: Optional[str] = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
