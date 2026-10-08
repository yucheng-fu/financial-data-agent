from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from financial_data_agent.config import get_llm_model


def build_chat_model() -> BaseChatModel:
    """Build the chat model for the current configuration.

    The API key is read from `GOOGLE_API_KEY` by the library.

    Returns:
        A Gemini chat model for the configured model name.

    Raises:
        RuntimeError: If `LLM_MODEL` is not set.
    """
    return ChatGoogleGenerativeAI(model=get_llm_model())


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    """Return the shared chat model, building it on first use.

    Returns:
        The process wide chat model.

    Raises:
        RuntimeError: If `LLM_MODEL` is not set.
    """
    return build_chat_model()
