import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "AutonomePay"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./autonomepay.db")
    
    # LLM & OpenRouter Gateway
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    PRIMARY_MODEL: str = os.getenv("PRIMARY_MODEL", "openrouter/minimax/minimax-m3:free")
    SECONDARY_MODEL: str = os.getenv("SECONDARY_MODEL", "openrouter/minimax/minimax-m2.7:free")
    THIRD_MODEL: str = os.getenv("THIRD_MODEL", "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free")
    FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "openrouter/openrouter/free")
    
    # LangSmith Observability
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_TRACING_V2: str = "true" if os.getenv("LANGCHAIN_API_KEY") else "false"
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "AutonomePay-RevenueRecovery")
    
    # Razorpay Credentials / MCP
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_mock12345")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "mock_secret_67890")
    
    # Token Budget Limits
    MAX_SESSION_TOKEN_BUDGET: int = 4000

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
