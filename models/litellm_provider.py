"""
LiteLLM model provider implementation.

Supports 100+ LLM providers through LiteLLM's unified interface.
"""

import time
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
import litellm
from litellm import acompletion, ModelResponse as LiteLLMResponse

from models.interface import (
    ModelProvider,
    Message,
    ModelResponse,
    ModelError,
    ModelNotFoundError,
    ModelTimeoutError,
    ModelRateLimitError,
)


class LiteLLMProvider(ModelProvider):
    """LiteLLM provider implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LiteLLM provider.
        
        Args:
            config: Configuration dict with keys:
                - default_model: Default model to use
                - fallback_models: List of fallback models
                - timeout: Request timeout in seconds
                - temperature: Default temperature
                - max_tokens: Default max tokens
        """
        super().__init__(config)
        
        self.default_model = config.get("default_model", "ollama/llama3.2")
        self.fallback_models = config.get("fallback_models", [])
        self.timeout = config.get("timeout", 120)
        self.default_temperature = config.get("temperature", 0.7)
        self.default_max_tokens = config.get("max_tokens", 4096)
        
        # Set LiteLLM settings
        litellm.drop_params = True  # Drop unsupported params instead of erroring
        litellm.suppress_debug_info = True
    
    def _messages_to_litellm(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert our Message format to LiteLLM format."""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
    
    def _litellm_to_response(self, llm_response: LiteLLMResponse, model: str) -> ModelResponse:
        """Convert LiteLLM response to our ModelResponse format."""
        choice = llm_response.choices[0]
        
        return ModelResponse(
            content=choice.message.content or "",
            finish_reason=choice.finish_reason or "stop",
            model=model,
            usage={
                "prompt_tokens": llm_response.usage.prompt_tokens,
                "completion_tokens": llm_response.usage.completion_tokens,
                "total_tokens": llm_response.usage.total_tokens,
            },
            metadata={
                "id": llm_response.id,
                "created": llm_response.created,
            }
        )
    
    async def generate(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate a response using LiteLLM."""
        start_time = time.time()
        
        # Build model chain (primary + fallbacks)
        models_to_try = [self.default_model] + self.fallback_models
        
        litellm_messages = self._messages_to_litellm(messages)
        temp = temperature if temperature is not None else self.default_temperature
        max_tok = max_tokens if max_tokens is not None else self.default_max_tokens
        
        last_error = None
        
        for model in models_to_try:
            try:
                # Attempt generation with this model
                response = await asyncio.wait_for(
                    acompletion(
                        model=model,
                        messages=litellm_messages,
                        temperature=temp,
                        max_tokens=max_tok,
                        **kwargs
                    ),
                    timeout=self.timeout
                )
                
                # Update metrics
                latency = time.time() - start_time
                self.metrics.total_requests += 1
                self.metrics.total_tokens += response.usage.total_tokens
                self.metrics.average_latency = (
                    (self.metrics.average_latency * (self.metrics.total_requests - 1) + latency)
                    / self.metrics.total_requests
                )
                
                return self._litellm_to_response(response, model)
                
            except asyncio.TimeoutError:
                last_error = ModelTimeoutError(f"Model {model} timed out after {self.timeout}s")
                self.metrics.error_count += 1
                continue
                
            except Exception as e:
                # Check for specific error types
                error_msg = str(e).lower()
                
                if "rate limit" in error_msg or "429" in error_msg:
                    last_error = ModelRateLimitError(f"Rate limit exceeded for {model}")
                elif "not found" in error_msg or "404" in error_msg:
                    last_error = ModelNotFoundError(f"Model {model} not found")
                else:
                    last_error = ModelError(f"Error with {model}: {str(e)}")
                
                self.metrics.error_count += 1
                continue
        
        # All models failed
        raise last_error or ModelError("All models failed to generate response")
    
    async def stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response tokens using LiteLLM."""
        litellm_messages = self._messages_to_litellm(messages)
        temp = temperature if temperature is not None else self.default_temperature
        max_tok = max_tokens if max_tokens is not None else self.default_max_tokens
        
        try:
            response = await acompletion(
                model=self.default_model,
                messages=litellm_messages,
                temperature=temp,
                max_tokens=max_tok,
                stream=True,
                **kwargs
            )
            
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except asyncio.TimeoutError:
            raise ModelTimeoutError(f"Streaming timed out after {self.timeout}s")
        except Exception as e:
            raise ModelError(f"Streaming error: {str(e)}")
    
    async def list_models(self) -> List[str]:
        """
        List available models.
        
        Note: This returns the configured models, not all possible LiteLLM models.
        """
        return [self.default_model] + self.fallback_models
    
    async def validate_model(self, model_name: str) -> bool:
        """
        Validate if a model is available.
        
        Args:
            model_name: Model identifier (e.g., "ollama/llama3.2")
        
        Returns:
            True if model can be used
        """
        try:
            # Try a simple completion to test the model
            test_response = await asyncio.wait_for(
                acompletion(
                    model=model_name,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1,
                ),
                timeout=10
            )
            return True
        except Exception:
            return False
