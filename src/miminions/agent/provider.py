import os
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.test import TestModel

class ModelFactory:
    """Factory to create LLM models based on provider strings."""
    
    @staticmethod
    def create(provider_name: str, model_name: str = None):
        provider_name = provider_name.lower()
        
        if provider_name == "openrouter":
            # OpenRouter speaks the OpenAI API protocol
            model_name = model_name or "openai/gpt-oss-20b:free"
            provider = OpenAIProvider(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            )
            return OpenAIModel(model_name, provider=provider)
            
        elif provider_name == "openai":
            model_name = model_name or "gpt-4o"
            return OpenAIModel(model_name)
            
        elif provider_name == "anthropic":
            model_name = model_name or "claude-3-5-sonnet-latest"
            return AnthropicModel(model_name)
            
        elif provider_name == "gemini":
            model_name = model_name or "gemini-1.5-flash"
            return GeminiModel(model_name)
            
        elif provider_name == "test":
            return TestModel()
            
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
