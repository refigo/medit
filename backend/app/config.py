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

settings = Settings()
