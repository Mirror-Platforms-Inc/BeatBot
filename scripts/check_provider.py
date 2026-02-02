#!/usr/bin/env python3
"""
Script to verify Model Provider configuration (LiteLLM/OpenAI/Claude).
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import init_config, get_config
from models.litellm_provider import LiteLLMProvider
from models.interface import Message, MessageRole

async def check_provider():
    print("🤖 Checking Model Provider Configuration...")
    
    # Initialize config
    init_config()
    config = get_config()
    
    print(f"   Provider: {config.model.provider}")
    print(f"   Default Model: {config.model.default_model}")
    print(f"   Fallback Models: {config.model.fallback_models}")
    
    # Check if API keys are needed but missing
    model_name = config.model.default_model.lower()
    if "gpt" in model_name and not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OpenAI model selected but OPENAI_API_KEY not set.")
    if "claude" in model_name and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  Warning: Claude model selected but ANTHROPIC_API_KEY not set.")
        
    try:
        # Initialize provider
        provider_config = {
            'default_model': config.model.default_model,
            'fallback_models': config.model.fallback_models,
            'temperature': config.model.temperature,
            'max_tokens': 10  # Low token count for quick check
        }
        
        provider = LiteLLMProvider(provider_config)
        
        # Simple generation check
        print("\n   Attempting simple generation config check (dry run)...")
        # We don't actually call the API to save cost/time unless requested, 
        # but we can check if the model is valid via list_models or internal checks.
        
        available = await provider.validate_model(config.model.default_model)
        if available:
             print(f"   ✅ Model '{config.model.default_model}' seems reachable/valid.")
        else:
             print(f"   ⚠️  Model '{config.model.default_model}' validation failed (might be offline or invalid key).")
             
    except Exception as e:
        print(f"   ❌ Error initializing provider: {e}")
        return False
        
    print("\n✅ Provider check complete.")
    return True

if __name__ == "__main__":
    asyncio.run(check_provider())
