import os

from agno.models.google import Gemini
from agno.models.openai import OpenAIChat
from agno.models.openrouter import OpenRouter


def get_model(env_key: str):
    model_id = os.getenv(env_key)
    
    # Helper function to clean model ID for specific provider
    def clean_model_id(model_id: str, provider: str) -> str:
        """Remove provider prefix from model ID if present"""
        if not model_id:
            return model_id
        # Remove common provider prefixes for non-OpenRouter providers
        if provider != "openrouter":
            prefixes = ["openai/", "anthropic/", "google/", "meta/", "mistral/"]
            for prefix in prefixes:
                if model_id.startswith(prefix):
                    return model_id[len(prefix):]
        return model_id
    
    # Check which API keys are available
    if os.getenv("GOOGLE_API_KEY"):
        cleaned_id = clean_model_id(model_id, "google")
        return Gemini(id=cleaned_id or "gemini-2.5-flash")
    elif os.getenv("OPENROUTER_API_KEY"):
        # OpenRouter keeps the provider prefix
        return OpenRouter(id=model_id or "google/gemini-2.5-flash", max_tokens=None)
    elif os.getenv("OPENAI_API_KEY"):
        # Fallback to OpenAI if no other provider is configured
        cleaned_id = clean_model_id(model_id, "openai")
        return OpenAIChat(id=cleaned_id or "gpt-4o-mini")
    else:
        # Default fallback (will fail if no API key)
        return OpenRouter(id=model_id or "google/gemini-2.5-flash", max_tokens=None)
