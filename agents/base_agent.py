from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from models.schemas import QueryRequest, AgentResponse


class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def process_query(self, request: QueryRequest) -> AgentResponse:
        """Process a query and return a response."""
        pass
    
    @abstractmethod
    def can_handle(self, query: str) -> bool:
        """Determine if this agent can handle the given query."""
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return the capabilities of this agent."""
        return {
            "name": self.name,
            "description": self.description,
            "can_handle": "Custom logic in subclass"
        }
