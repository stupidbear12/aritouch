import os

SERVER_HOST = os.getenv("AIRTOUCH_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("AIRTOUCH_PORT", "8000"))
DB_PATH = os.getenv("AIRTOUCH_DB", "airtouch.db")
CORS_ORIGINS = os.getenv("AIRTOUCH_CORS", "*").split(",")
