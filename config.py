# config.py
 
import os
from dotenv import load_dotenv

load_dotenv()  # loads .env file automatically

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL             = "claude-haiku-4-5-20251001"
MAX_TOKENS        = 6000
TOP_STOCKS        = 8      # how many stocks to discover and analyze
LOOKBACK_HOURS    = 48     # how recent the news should be