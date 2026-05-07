"""
Configuration and environment setup for the auto-apply-agent.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LLM Configuration
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))

# Browser Configuration
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))  # ms
PAGE_WAIT_TIMEOUT = int(os.getenv("PAGE_WAIT_TIMEOUT", "10000"))  # ms

# Automation Configuration
FIELD_FILL_DELAY_MIN = int(os.getenv("FIELD_FILL_DELAY_MIN", "500"))  # ms
FIELD_FILL_DELAY_MAX = int(os.getenv("FIELD_FILL_DELAY_MAX", "1500"))  # ms
VALIDATION_RETRY_MAX = int(os.getenv("VALIDATION_RETRY_MAX", "2"))
CHECKPOINT_INTERVAL = int(os.getenv("CHECKPOINT_INTERVAL", "3"))  # Save every N fields

# Session Configuration
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))

# File Paths (relative to project root)
PROFILE_FILE = os.getenv("PROFILE_FILE", "profile.json")
SESSION_FILE = os.getenv("SESSION_FILE", ".session.json")
CHECKPOINT_FILE = os.getenv("CHECKPOINT_FILE", ".checkpoint.json")
LOG_FILE = os.getenv("LOG_FILE", "application.log")

# Validation
if not LLM_API_KEY:
    raise ValueError("LLM_API_KEY environment variable is not set. Please set it before running the agent.")


def validate_config():
    """Validate that all required configuration values are set."""
    required_vars = [LLM_API_KEY, LLM_MODEL]
    if not all(required_vars):
        raise ValueError("Missing required configuration. Check LLM_API_KEY and LLM_MODEL.")
