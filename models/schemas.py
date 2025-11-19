"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class QueryRequest(BaseModel):
    """Request model for user queries."""
    query: str = Field(..., description="User's query text")
    session_id: Optional[str] = Field(None, description="Session identifier for conversation tracking")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class AgentResponse(BaseModel):
    """Response model from agents."""
    agent_name: str = Field(..., description="Name of the agent that processed the request")
    response: str = Field(..., description="The agent's response text")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional structured data")
    success: bool = Field(True, description="Whether the request was successful")
    error: Optional[str] = Field(None, description="Error message if unsuccessful")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class ProductModel(BaseModel):
    """Product model matching the catalog database schema."""
    id: int
    sku: str
    name: str
    category: str
    unit_price: float
    unit_of_measure: str  # Changed from 'unit' to match database
    quantity_on_hand: int
    description: Optional[str] = None
    specifications: Optional[str] = None

    class Config:
        from_attributes = True



class CompanyLocation(BaseModel):
    """Company location model."""
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: Optional[str] = None
    type: Optional[str] = None  # e.g., "headquarters", "warehouse"



class InvoiceItem(BaseModel):
    """Invoice line item model."""
    sku: str
    description: str
    quantity: int
    unit_price: float
    total: float
