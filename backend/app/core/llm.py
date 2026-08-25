from __future__ import annotations

import logging
from typing import Any
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger("studyassistant.llm")

# Ordered list of models to try if the primary model hits 429 quota exhaustion
FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
    "gemini-2.5-pro",
    "gemini-pro-latest",
]


def invoke_gemini_with_fallback(
    messages: list[BaseMessage],
    api_key: str,
    preferred_model: str = "gemini-3.6-flash",
    temperature: float = 0.2,
) -> Any:
    """Invokes Gemini with automatic cascade fallback across model tiers if 429 Quota is hit."""
    models_to_try = [preferred_model] + [m for m in FALLBACK_MODELS if m != preferred_model]
    last_error: Exception | None = None

    for model_name in models_to_try:
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=temperature,
            )
            result = llm.invoke(messages)
            logger.info(f"Successfully invoked model '{model_name}'")
            return result
        except Exception as exc:
            err_str = str(exc)
            logger.warning(f"Model '{model_name}' failed: {err_str[:120]}")
            last_error = exc
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "404" in err_str or "NOT_FOUND" in err_str:
                # Try next model in fallback list
                continue
            else:
                raise exc

    if last_error:
        raise last_error
    raise RuntimeError("No Gemini models available.")