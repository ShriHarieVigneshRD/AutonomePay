import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables or backend/.env (env vars win)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "AutonomePay"
    API_V1_STR: str = "/api"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite:///./autonomepay.db"

    # Web / security
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,https://autonome-pay.vercel.app"
    PUBLIC_APP_URL: str = "http://localhost:5173"  # where sandbox payment links point
    ADMIN_TOKEN: str = ""  # if set, starting benchmark runs requires the X-Admin-Token header
    CHAT_RATE_LIMIT_PER_MIN: int = 30  # per client IP

    # LLM via LiteLLM → OpenRouter, tried in this order
    OPENROUTER_API_KEY: str = ""
    PRIMARY_MODEL: str = "openrouter/minimax/minimax-m3:free"
    SECONDARY_MODEL: str = "openrouter/minimax/minimax-m2.7:free"
    THIRD_MODEL: str = "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"
    FALLBACK_MODEL: str = "openrouter/openrouter/free"
    LLM_MAX_TOKENS: int = 800
    MAX_SESSION_TOKEN_BUDGET: int = 6000

    # LangSmith (optional)
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_PROJECT: str = "AutonomePay-RevenueRecovery"

    # Razorpay; key ids starting with "rzp_test_mock" mean sandbox links
    RAZORPAY_KEY_ID: str = "rzp_test_mock12345"
    RAZORPAY_KEY_SECRET: str = "mock_secret_67890"
    # Payment tools are called over MCP: embedded | remote | stdio (see app/payments/mcp_client.py)
    RAZORPAY_MCP_MODE: Literal["embedded", "remote", "stdio"] = "embedded"
    RAZORPAY_MCP_URL: str = "https://mcp.razorpay.com/mcp"
    RAZORPAY_MCP_COMMAND: str = ""  # e.g. "razorpay-mcp-server stdio" for Razorpay's binary

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def model_chain(self) -> list[str]:
        return [self.PRIMARY_MODEL, self.SECONDARY_MODEL, self.THIRD_MODEL, self.FALLBACK_MODEL]

    @property
    def langsmith_enabled(self) -> bool:
        return bool(self.LANGCHAIN_API_KEY) and self.LANGCHAIN_TRACING_V2


settings = Settings()

# The langsmith SDK reads its switches from os.environ, not from our settings object.
if settings.langsmith_enabled:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGCHAIN_API_KEY)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGCHAIN_PROJECT)
