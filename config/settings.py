import os

from dotenv import load_dotenv

load_dotenv()

JQUANTS_API_KEY = os.getenv(
    "JQUANTS_API_KEY",
    ""
)

IRBANK_API_KEY = os.getenv(
    "IRBANK_API_KEY",
    ""
)

IRBANK_BASE_URL = "https://api.irbank.net/v1"