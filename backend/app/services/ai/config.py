"""
AI Layer Configuration
Loads provider settings from environment variables.
Never hardcode API keys — they must come from the environment.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("ai_config")

# Load env from backend root (app/services/ai -> app/services -> app -> backend)
_backend_dir = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(dotenv_path=_backend_dir / ".env")
load_dotenv()


class AIConfig:
    """AI provider configuration loaded from environment variables."""

    PROVIDER: str = os.getenv("AI_PROVIDER", "google")
    MODEL: str = os.getenv("AI_MODEL", "gemini-3.5-flash-lite")
    API_KEY: str = os.getenv("AI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    MAX_OUTPUT_TOKENS: int = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "4096"))
    TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.3"))

    # Safety: rate limiting
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("AI_MAX_REQUESTS_PER_MINUTE", "30"))

    @classmethod
    def is_configured(cls) -> bool:
        """Check if AI is properly configured with an API key."""
        return bool(cls.API_KEY)

    @classmethod
    def get_model_display(cls) -> str:
        """Human-readable model identifier."""
        return f"{cls.PROVIDER}/{cls.MODEL}"

    @classmethod
    def reload(cls):
        """Re-read environment variables (useful after .env changes)."""
        load_dotenv(dotenv_path=_backend_dir / ".env", override=True)
        load_dotenv(override=True)
        cls.PROVIDER = os.getenv("AI_PROVIDER", "google")
        cls.MODEL = os.getenv("AI_MODEL", "gemini-2.0-flash")
        cls.API_KEY = os.getenv("AI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        cls.MAX_OUTPUT_TOKENS = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "4096"))
        cls.TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.3"))
        cls.MAX_REQUESTS_PER_MINUTE = int(os.getenv("AI_MAX_REQUESTS_PER_MINUTE", "30"))
