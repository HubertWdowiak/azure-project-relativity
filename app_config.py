import os

CLIENT_ID = "012275a0-ad90-44bb-b5c4-0badba1f7136" # Application (client) ID of app registration

CLIENT_SECRET = "lIS8Q~x9FKlFM63hQ1CbWXdZ8_dMCvO8.Y0Ancbd" # Placeholder - for use ONLY during testing.
# In a production app, we recommend you use a more secure method of storing your secret,
# like Azure Key Vault. Or, use an environment variable as described in Flask's documentation:
# https://flask.palletsprojects.com/en/1.1.x/config/#configuring-from-environment-variables
# CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# if not CLIENT_SECRET:
#     raise ValueError("Need to define CLIENT_SECRET environment variable")


AUTHORITY = "https://login.microsoftonline.com/02b063b5-c529-4148-824c-4db8b3d36d2c"  # For multi-tenant app
REDIRECT_PATH = "/getAToken"
ENDPOINT = 'https://graph.microsoft.com/v1.0/users'  # This resource requires no admin consent
SCOPE = ["User.ReadBasic.All"]
SESSION_TYPE = "filesystem"