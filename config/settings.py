import os
from dotenv import load_dotenv

load_dotenv()

# The OpenAI API key is not required when using a local VLLM service.
# The key can be a placeholder string.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "not-needed")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
# NEWS_API_KEY is temporarily removed.
# NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "http://192.168.157.169:5003/v1")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "Qwen/Qwen3-14B-AWQ")
