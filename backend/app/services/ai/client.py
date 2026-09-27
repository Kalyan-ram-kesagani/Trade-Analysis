"""
AI Client — Provider Abstraction
Wraps the Google Generative AI SDK with a clean interface.
Can be swapped to another provider by modifying this single file.
"""

import json
import logging
from typing import Any, Dict, Optional

from app.services.ai.config import AIConfig

logger = logging.getLogger("ai_client")

# Lazy-loaded client instance
_client = None


def _get_client():
    """Lazy-initialize the AI client."""
    global _client
    if _client is None:
        if not AIConfig.is_configured():
            raise RuntimeError(
                "AI is not configured. Set AI_API_KEY in your environment."
            )
        from google import genai
        _client = genai.Client(api_key=AIConfig.API_KEY)
    return _client


async def generate_structured(
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Send a prompt to the AI model and return parsed JSON.

    Args:
        system_prompt: System instruction defining the AI's role and output format.
        user_prompt: The user-facing prompt with context data.
        temperature: Override default temperature.
        max_tokens: Override default max output tokens.

    Returns:
        Parsed JSON dict from the AI response.

    Raises:
        RuntimeError: If AI is not configured or response is invalid.
        ValueError: If AI response cannot be parsed as JSON.
    """
    from google import genai

    client = _get_client()

    temp = temperature if temperature is not None else AIConfig.TEMPERATURE
    max_tok = max_tokens if max_tokens is not None else AIConfig.MAX_OUTPUT_TOKENS

    fallback_models = [
        AIConfig.MODEL,
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-flash-latest",
    ]
    # Deduplicate preserving order
    seen = set()
    models_to_try = [m for m in fallback_models if not (m in seen or seen.add(m))]

    last_error = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temp,
                    max_output_tokens=max_tok,
                    response_mime_type="application/json",
                ),
            )
            raw_text = response.text
            if not raw_text:
                raise ValueError("AI returned an empty response")

            # Parse JSON response
            parsed = json.loads(raw_text)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"AI returned invalid JSON: {e}")
            raise ValueError(f"AI response was not valid JSON: {e}")
        except Exception as e:
            last_error = e
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str or "404" in err_str:
                logger.warning(f"Model {model_name} failed with {e}, trying next fallback...")
                continue
            logger.error(f"AI generation failed: {e}")
            raise

    if last_error:
        raise last_error
    raise RuntimeError("AI generation returned no response across all candidate models.")


def get_token_count(response) -> Optional[int]:
    """Extract token count from response metadata if available."""
    try:
        if hasattr(response, "usage_metadata"):
            meta = response.usage_metadata
            return (
                getattr(meta, "total_token_count", None)
                or getattr(meta, "candidates_token_count", None)
            )
    except Exception:
        pass
    return None
