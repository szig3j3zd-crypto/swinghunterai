import os

from dotenv import load_dotenv

load_dotenv()

JQUANTS_API_KEY = os.getenv(
    "JQUANTS_API_KEY",
    ""
)