import os
from dotenv import load_dotenv

load_dotenv()

# LLM
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "anthropic/claude-3.5-haiku")

# Zep
ZEP_API_KEY = os.getenv("ZEP_API_KEY")

# Tavily
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# App
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24).hex())