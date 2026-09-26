import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        f"DATABASE_URL is not configured. Expected .env at: {ENV_FILE}"
    )

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args={
        "statement_cache_size": 0
    },
)