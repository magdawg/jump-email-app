import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Disable strict scope checking in oauthlib
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

DATABASE_URL = os.getenv("DATABASE_URL")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
