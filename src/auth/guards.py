from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.auth.oauth import get_user_info, login_token_store, youtube_token_store, refresh_access_token
from src.config.settings import logger
from datetime import datetime

# Define security schemes with explicit header names
login_scheme = HTTPBearer(auto_error=False)  # Uses "Authorization" header
youtube_scheme = HTTPBearer(scheme_name="YouTube-Authorization", auto_error=False)  # Uses custom "YouTube-Authorization" header

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(login_scheme)):
    """Authentication guard for general Google login"""
    print(login_token_store)
    if not token:
        raise HTTPException(status_code=401, detail="No login token provided")
    try:
        user_info = await get_user_info(token.credentials)
        user_id = user_info["sub"]
        if user_id not in login_token_store:
            raise HTTPException(status_code=401, detail="Invalid login token")
        
        stored_token = login_token_store[user_id]
        if stored_token["access_token"] != token.credentials:
            raise HTTPException(status_code=401, detail="Login token mismatch")
        
        if datetime.utcnow() > stored_token["expires_at"]:
            logger.info(f"Login token expired for user {user_id}, attempting refresh")
            new_token = await refresh_access_token(user_id, "google")
            stored_token["access_token"] = new_token
        
        return user_info
    except Exception as e:
        logger.error(f"Login authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid or expired login token")

async def get_youtube_user(token: HTTPAuthorizationCredentials = Depends(youtube_scheme)):
    """Authentication guard for YouTube upload authorization"""
    if not token:
        raise HTTPException(status_code=401, detail="No YouTube token provided")
    try:
        user_id = None
        for uid, tokens in youtube_token_store.items():
            if tokens["access_token"] == token.credentials:
                user_id = uid
                break
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid YouTube token")
        
        stored_token = youtube_token_store[user_id]
        if datetime.utcnow() > stored_token["expires_at"]:
            logger.info(f"YouTube token expired for user {user_id}, attempting refresh")
            new_token = await refresh_access_token(user_id, "youtube")
            stored_token["access_token"] = new_token
        
        return {"user_id": user_id}
    except Exception as e:
        logger.error(f"YouTube authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid or expired YouTube token")