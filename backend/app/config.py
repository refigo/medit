import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # Database settings
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/medit")
    
    # API settings
    API_V1_STR = "/api/v1"
    
    # Security settings
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-development")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
    
    # LLM Service settings
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # 기본값: openai
    
    # OpenAI settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # AWS Bedrock settings
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-opus-20240229-v1:0")

settings = Settings()
