from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core.config import settings


def get_nvidia_model() -> OpenAIChatModel:
    return OpenAIChatModel(
        model_name=settings.NVIDIA_MODEL,
        provider=OpenAIProvider(
            base_url=settings.NVIDIA_BASE_URL,
            api_key=settings.NVIDIA_API_KEY,
        ),
    )
