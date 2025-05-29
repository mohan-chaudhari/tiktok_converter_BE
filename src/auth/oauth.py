from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from src.config.settings import config, logger
from datetime import datetime, timedelta

# In-memory token stores
login_token_store = {}  # For general login
youtube_token_store = {}  # For YouTube-specific tokens

# Load environment variables
config_env = Config(".env")
oauth = OAuth(config_env)

# General Google login (openid, email, profile)
oauth.register(
    name="google",
    client_id=config.GOOGLE_CLIENT_ID,
    client_secret=config.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
    redirect_uri=config.GOOGLE_REDIRECT_URI,
)

# YouTube-specific OAuth (youtube.upload)
oauth.register(
    name="youtube",
    client_id=config.YOUTUBE_CLIENT_ID,
    client_secret=config.YOUTUBE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    authorize_params={
        "access_type": "offline",  # Request a refresh token
        "prompt": "consent",      # Force the consent screen to ensure refresh token
        "include_granted_scopes": "true"  # Include previously granted scopes
    },
    client_kwargs={
        "scope": "https://www.googleapis.com/auth/youtube.upload",
    },
    redirect_uri=config.YOUTUBE_REDIRECT_URI,
)

async def get_access_token(code: str, redirect_uri: str, client_type: str = "google"):
    """Exchange authorization code for access token"""
    try:
        client = oauth.google if client_type == "google" else oauth.youtube
        token = await client.authorize_access_token({"code": code, "redirect_uri": redirect_uri})
        user_info = await client.userinfo(token=token) if client_type == "google" else None
        user_id = user_info["sub"] if user_info else token["sub"]
        store = login_token_store if client_type == "google" else youtube_token_store
        store[user_id] = {
            "access_token": token["access_token"],
            "refresh_token": token.get("refresh_token"),
            "expires_at": datetime.utcnow() + timedelta(seconds=token["expires_in"]),
        }
        logger.info(f"Stored {client_type} tokens for user {user_id}")
        return {"access_token": token["access_token"], "user_id": user_id}
    except Exception as e:
        logger.error(f"Failed to get {client_type} access token: {str(e)}")
        raise

async def refresh_access_token(user_id: str, client_type: str = "google"):
    """Refresh an expired access token"""
    store = login_token_store if client_type == "google" else youtube_token_store
    client = oauth.google if client_type == "google" else oauth.youtube
    if user_id not in store or not store[user_id].get("refresh_token"):
        raise ValueError(f"No refresh token available for {client_type}")
    try:
        token = await client.refresh_token(refresh_token=store[user_id]["refresh_token"])
        store[user_id].update({
            "access_token": token["access_token"],
            "expires_at": datetime.utcnow() + timedelta(seconds=token["expires_in"]),
        })
        logger.info(f"Refreshed {client_type} token for user {user_id}")
        return token["access_token"]
    except Exception as e:
        logger.error(f"Failed to refresh {client_type} token: {str(e)}")
        raise

async def get_user_info(access_token: str):
    """Get user info from Google using access token"""
    if not access_token:
        logger.error("No access token provided")
        raise ValueError("No access token provided")

    # Log token for debugging (masked)
    masked_token = access_token[:4] + "****" + access_token[-4:] if len(access_token) > 8 else "****"
    logger.info(f"Getting user info with token: {masked_token}")

    # Check if token exists in login_token_store
    user_id_from_store = None
    for uid, token_data in login_token_store.items():
        if token_data.get("access_token") == access_token:
            user_id_from_store = uid
            logger.info(f"Found token in store for user: {uid}")
            break

    try:
        # Try to get user info from Google API
        user_info = await oauth.google.userinfo(token={"access_token": access_token})

        if not user_info or "sub" not in user_info:
            logger.error("Invalid user info response from Google")
            raise ValueError("Invalid user info response")

        user_id = user_info["sub"]
        logger.info(f"Successfully retrieved user info for user ID: {user_id}")

        # If we found the token in the store but for a different user, log a warning
        if user_id_from_store and user_id_from_store != user_id:
            logger.warning(f"Token mismatch: store has {user_id_from_store}, API returned {user_id}")

        # If user not in store, add it
        if user_id not in login_token_store:
            logger.info(f"Adding user {user_id} to login_token_store")
            login_token_store[user_id] = {
                "access_token": access_token,
                "refresh_token": None,
                "expires_at": datetime.utcnow() + timedelta(hours=1)  # Assume 1 hour validity
            }

        return user_info
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to get user info: {error_msg}")

        # If we found the token in the store, return cached user info
        if user_id_from_store:
            logger.info(f"Using cached user info for {user_id_from_store}")
            return {"sub": user_id_from_store, "email": "cached@user.info", "name": "Cached User"}

        raise ValueError(f"Failed to validate token: {error_msg}")