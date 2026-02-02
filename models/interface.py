"""
Abstract interface for model providers.

Allows swapping between different LLM providers (LiteLLM, Ollama, etc.)
without changing the core agent code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, List, Dict, Any, Optional
from enum import Enum


class MessageRole(str, Enum):
    """Message role enumeration."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


@dataclass
class Message:
    """Represents a conversation message."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ModelResponse:
    """Response from model generation."""
    content: str
    finish_reason: str  # "stop", "length", "error"
    model: str
    usage: Dict[str, int]  # {"prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...}
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ModelMetrics:
    """Metrics for model usage tracking."""
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    average_latency: float = 0.0
    error_count: int = 0


class ModelProvider(ABC):
    """
    Abstract base class for model providers.
    
    All model providers (LiteLLM, Ollama, etc.) must implement this interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize model provider.
        
        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.metrics = ModelMetrics()
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """
        Generate a response from the model.
        
        Args:
            messages: List of conversation messages
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
        
        Returns:
            ModelResponse object
        
        Raises:
            ModelError: If generation fails
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream response tokens from the model.
        
        Args:
            messages: List of conversation messages
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
        
        Yields:
            Response tokens as they are generated
        
        Raises:
            ModelError: If streaming fails
        """
        pass
    
    @abstractmethod
    async def list_models(self) -> List[str]:
        """
        List available models for this provider.
        
        Returns:
            List of model identifiers
        """
        pass
    
    @abstractmethod
    async def validate_model(self, model_name: str) -> bool:
        """
        Check if a model is available.
        
        Args:
            model_name: Model identifier
        
        Returns:
            True if model is available, False otherwise
        """
        pass
    
    def get_metrics(self) -> ModelMetrics:
        """
        Get usage metrics for this provider.
        
        Returns:
            ModelMetrics object
        """
        return self.metrics
    
    def reset_metrics(self) -> None:
        """Reset usage metrics."""
        self.metrics = ModelMetrics()


class ModelError(Exception):
    """Base exception for model-related errors."""
    pass


class ModelNotFoundError(ModelError):
    """Raised when specified model is not available."""
    pass


class ModelTimeoutError(ModelError):
    """Raised when model request times out."""
    pass


class ModelRateLimitError(ModelError):
    """Raised when rate limit is exceeded."""
    pass
