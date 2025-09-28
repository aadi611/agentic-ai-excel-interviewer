import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class Config:
    """Application configuration"""
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    PORT = int(os.getenv("PORT", 8000))
    
    # Groq model selection (fastest to most capable)
    MODELS = {
        "fast": "llama3-8b-8192",        # Fastest, good quality
        "balanced": "llama3-70b-8192",   # Best balance
        "quality": "mixtral-8x7b-32768", # Highest quality
    }
    
    DEFAULT_MODEL = MODELS["balanced"]
    
    # Interview settings
    MAX_QUESTIONS = 10
    SESSION_TIMEOUT = 3600  # 1 hour in seconds
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in .env file")
        return True