import os

CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTHORITY = os.environ.get("AUTHORITY")
REDIRECT_PATH = "/getAToken"
SCOPE = ["User.ReadBasic.All"]
SESSION_TYPE = "filesystem"