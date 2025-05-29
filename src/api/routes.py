from fastapi import APIRouter, HTTPException, Depends, Query, Request, Body
import httpx  # For direct HTTP requests
from src.dtos.download_dto import DownloadRequestDTO, DownloadResponseDTO
from src.dtos.convert_dto import ConvertRequestDTO, ConvertResponseDTO
from src.dtos.video_dto import VideoListResponseDTO
from src.services.downloader import download_tiktok_video
from src.services.converter import convert_video_for_youtube
from src.services.youtube import upload_to_youtube  # Import the YouTube upload function
from src.services.youtube_direct import upload_with_direct_credentials  # Import direct upload function
from src.services.file_service import get_downloaded_videos, get_converted_videos
from src.auth.guards import get_current_user
from src.auth.oauth import oauth, login_token_store, youtube_token_store  # Import token stores
from src.config.settings import config, logger
from datetime import datetime, timedelta
from fastapi.responses import RedirectResponse, FileResponse
from typing import List
import os

# JWT imports are not used but might be needed in the future
# from jwt import PyJWT, DecodeError, ExpiredSignatureError
# import jwt

router = APIRouter(tags=["tiktok-youtube-converter-poc"])

@router.get("/auth/login")
async def login(request: Request):
    """Redirect to Google OAuth2 login page for general authentication."""
    redirect_uri = config.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        token_data = await oauth.google.authorize_access_token(request)
        user_info = await oauth.google.userinfo(token=token_data)
        user_id = user_info["sub"]
        login_token_store[user_id] = {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": datetime.utcnow() + timedelta(seconds=token_data["expires_in"]),
        }
        logger.info(f"User {user_id} authenticated successfully")
        
        # Redirect to frontend with token and user info as query parameters
        frontend_url = config.FRONTEND_URL or "http://localhost:8080"
        redirect_url = f"{frontend_url}/auth/callback?access_token={token_data['access_token']}&user={user_info['sub']}"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.error(f"Auth callback failed: {str(e)} - Request: {request.query_params}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

# @router.get("/youtube/auth")
# async def youtube_auth(request: Request, user=Depends(get_current_user)):
#     """Redirect to Google OAuth2 for YouTube upload permission."""
#     redirect_uri = config.YOUTUBE_REDIRECT_URI
#     return await oauth.youtube.authorize_redirect(request, redirect_uri)

# @router.get("/youtube/callback")
# async def youtube_callback(request: Request):
#     """Handle YouTube OAuth2 callback and store tokens."""
#     try:
#         token_data = await oauth.youtube.authorize_access_token(request)
#         user_id = token_data["sub"]  # Use sub from token if no userinfo
#         youtube_token_store[user_id] = {
#             "access_token": token_data["access_token"],
#             "refresh_token": token_data.get("refresh_token"),
#             "expires_at": datetime.utcnow() + timedelta(seconds=token_data["expires_in"]),
#         }
#         logger.info(f"YouTube authorization completed for user {user_id}")
#         return {"youtube_access_token": token_data["access_token"], "user_id": user_id}
#     except Exception as e:
#         logger.error(f"YouTube callback failed: {str(e)} - Request: {request.query_params}")
#         raise HTTPException(status_code=400, detail=f"YouTube authentication failed: {str(e)}")

@router.get("/youtube/auth")
async def youtube_auth(
    request: Request,
    token: str = Query(None, description="Bearer token"),
    force_consent: bool = Query(False, description="Force consent screen even if previously authorized")
):
    """Redirect to Google OAuth2 for YouTube upload permission."""
    if not token:
        raise HTTPException(status_code=401, detail="Token required")

    # Strip 'Bearer ' prefix if present
    if token.startswith("Bearer "):
        token = token[7:]

    # Validate token and get user info
    try:
        user_info = await oauth.google.userinfo(token={"access_token": token})
        user_id = user_info["sub"]
        
        # Store user_id and token in session
        request.session["user_id"] = user_id
        request.session["auth_token"] = token

        # If force_consent is true, revoke any existing YouTube tokens for this user
        if force_consent and user_id in youtube_token_store:
            logger.info(f"Force consent requested. Removing existing YouTube tokens for user {user_id}")
            try:
                old_token = youtube_token_store[user_id]["access_token"]
                revoke_url = "https://oauth2.googleapis.com/revoke"
                async with httpx.AsyncClient() as client:
                    await client.post(revoke_url, params={"token": old_token})
                    logger.info(f"Successfully revoked old token for user {user_id}")
            except Exception as revoke_error:
                logger.warning(f"Failed to revoke token: {str(revoke_error)}")

            del youtube_token_store[user_id]

        redirect_uri = config.YOUTUBE_REDIRECT_URI

        # Add additional parameters to force refresh token
        extra_params = {
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true"
        }

        logger.info(f"Redirecting to YouTube authorization with params: {extra_params}")
        return await oauth.youtube.authorize_redirect(request, redirect_uri, **extra_params)

    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@router.get("/youtube/callback")
async def youtube_callback(request: Request):
    """Handle YouTube OAuth2 callback, store tokens, and redirect to frontend with token."""
    logger.info(f"Callback request URL: {request.url}")
    logger.info(f"Callback query parameters: {request.query_params}")
    logger.info(f"Callback headers: {request.headers}")
    logger.info(f"Session data: {request.session}")
    
    try:
        # Check for OAuth error in query parameters
        if "error" in request.query_params:
            error = request.query_params["error"]
            logger.error(f"OAuth error in callback: {error}")
            raise HTTPException(status_code=400, detail=f"YouTube authentication failed: {error}")

        # Verify session data
        user_id = request.session.get("user_id")
        auth_token = request.session.get("auth_token")
        
        if not user_id or not auth_token:
            logger.error("Missing session data in callback: user_id=%s, auth_token=%s", user_id, auth_token)
            raise HTTPException(status_code=400, detail="Invalid session state")

        # Get token data from the callback
        logger.info("Attempting to exchange authorization code for token")
        token_data = await oauth.youtube.authorize_access_token(request)
        if not token_data.get("access_token"):
            logger.error("No access token received from token exchange")
            raise HTTPException(status_code=400, detail="Failed to obtain YouTube access token")

        # Log token data for debugging (with sensitive info masked)
        safe_token_data = {k: (v[:10] + '...' if isinstance(v, str) and k != 'expires_in' else v) for k, v in token_data.items()}
        logger.info(f"YouTube token data received: {safe_token_data}")

        # Store tokens
        logger.info(f"Updating youtube_token_store for user_id: {user_id}")
        youtube_token_store[user_id] = {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": datetime.utcnow() + timedelta(seconds=token_data["expires_in"]),
        }

        # Clear session data
        logger.info("Clearing session data for user_id: %s", user_id)
        request.session.pop("user_id", None)
        request.session.pop("auth_token", None)

        # Redirect to frontend with token
        frontend_url = config.FRONTEND_URL or "http://localhost:8080"
        redirect_url = f"{frontend_url}/youtube/callback?youtube_access_token={token_data['access_token']}&user_id={user_id}"
        logger.info(f"Redirecting to frontend: {redirect_url}")
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        logger.error(f"YouTube callback failed: {str(e)}", exc_info=True)
        # Clear session data on error
        request.session.pop("user_id", None)
        request.session.pop("auth_token", None)
        # Redirect to frontend with error
        frontend_url = config.FRONTEND_URL or "http://localhost:8080"
        error_redirect_url = f"{frontend_url}/youtube/callback?error={str(e)}"
        logger.info(f"Redirecting to frontend with error: {error_redirect_url}")
        return RedirectResponse(url=error_redirect_url)

@router.post("/download", response_model=DownloadResponseDTO, dependencies=[Depends(get_current_user)])
async def download_video(request: DownloadRequestDTO, user=Depends(get_current_user)):
    """Download a TikTok video using the provided URL.

    Args:
        request (DownloadRequestDTO): The request body containing the TikTok URL and optional output folder.
        user: Authenticated user info from Google OAuth2 (requires Bearer token).

    Returns:
        DownloadResponseDTO: Details about the downloaded video.
    """
    try:
        logger.info(f"User {user['sub']} initiated download for URL: {request.url}")
        result = await download_tiktok_video(request.url, request.output_folder)
        return DownloadResponseDTO(**result)
    except Exception as e:
        logger.error(f"Download failed for user {user['sub']}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/convert", response_model=ConvertResponseDTO, dependencies=[Depends(get_current_user)])
async def convert_video(request: ConvertRequestDTO, user=Depends(get_current_user)):
    """Convert a downloaded video to a YouTube-compatible format.

    Args:
        request (ConvertRequestDTO): The request body containing input path, optional output folder, and quality.
        user: Authenticated user info from Google OAuth2 (requires Bearer token).

    Returns:
        ConvertResponseDTO: Details about the converted video.
    """
    try:
        logger.info(f"User {user['sub']} initiated conversion for file: {request.input_path}")
        result = await convert_video_for_youtube(
            request.input_path, request.output_folder, request.quality
        )
        return ConvertResponseDTO(**result)
    except Exception as e:
        logger.error(f"Conversion failed for user {user['sub']}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/user", dependencies=[Depends(get_current_user)])
async def get_user_info(user=Depends(get_current_user)):
    """Retrieve authenticated user's information.

    Args:
        user: Authenticated user info from Google OAuth2 (requires Bearer token).

    Returns:
        dict: User information from Google (e.g., email, name).
    """
    try:
        logger.info(f"User {user['sub']} requested their info")
        return {
            "user_id": user["sub"],
            "email": user.get("email"),
            "name": user.get("name"),
            "picture": user.get("picture"),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve user info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user info")

@router.post("/youtube/upload")
async def upload_video(
    request: Request,
    file_path: str = Body(...),
    title: str = Body(...),
    description: str = Body(""),
    login_token: str = Body(None),
    youtube_token: str = Body(None),
    youtube_refresh_token: str = Body(None),
    tags: List[str] = Body(None),
):
    """Upload a converted video to YouTube.

    Args:
        file_path (str): Path to the converted video file.
        title (str): Video title.
        description (str): Video description (optional).
        login_token (str): Google login token (can be provided in body instead of header).
        youtube_token (str): YouTube authorization token (can be provided in body instead of header).
        tags (List[str]): List of video tags (optional).

    Returns:
        dict: Video ID and URL.
    """
    try:
        # Get tokens from request headers if not provided in body
        if not login_token or not youtube_token:
            # Try to get from authorization headers
            auth_header = request.headers.get("Authorization")
            youtube_auth_header = request.headers.get("YouTube-Authorization")

            if auth_header and auth_header.startswith("Bearer "):
                login_token = login_token or auth_header.replace("Bearer ", "")
            if youtube_auth_header and youtube_auth_header.startswith("Bearer "):
                youtube_token = youtube_token or youtube_auth_header.replace("Bearer ", "")

        # Log token information for debugging
        logger.info(f"YouTube upload request - Login token provided: {bool(login_token)}, YouTube token provided: {bool(youtube_token)}")

        # Validate tokens
        if not login_token:
            raise HTTPException(status_code=401, detail="Login token is required")
        if not youtube_token:
            raise HTTPException(status_code=401, detail="YouTube token is required")

        # Validate login token and get user info
        try:
            # First check if token exists in store
            login_user_id_from_store = None
            for uid, token_data in login_token_store.items():
                if token_data.get("access_token") == login_token:
                    login_user_id_from_store = uid
                    logger.info(f"Found login token in store for user: {uid}")
                    break

            # Try to get user info from Google API
            try:
                user_info = await oauth.google.userinfo(token={"access_token": login_token})
                user_id = user_info["sub"]
                logger.info(f"Successfully validated login token for user: {user_id}")
            except Exception as api_error:
                # If API call fails but we found the token in store, use that
                if login_user_id_from_store:
                    logger.warning(f"API call failed but token found in store. Using cached user ID: {login_user_id_from_store}")
                    user_id = login_user_id_from_store
                    # Add token to store if not already there
                    if user_id not in login_token_store:
                        login_token_store[user_id] = {
                            "access_token": login_token,
                            "refresh_token": None,
                            "expires_at": datetime.now() + timedelta(hours=1)
                        }
                else:
                    # No token in store and API call failed
                    logger.error(f"Login token validation failed: {str(api_error)}")
                    raise HTTPException(status_code=401, detail=f"Invalid login token: {str(api_error)}")
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login token validation: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Server error during token validation: {str(e)}")

        # Validate YouTube token
        youtube_user_id = None
        for uid, tokens in youtube_token_store.items():
            if tokens["access_token"] == youtube_token:
                youtube_user_id = uid
                logger.info(f"Found YouTube token in store for user: {uid}")
                break

        # If YouTube token not found in store, add it using the login user ID
        if not youtube_user_id:
            logger.warning(f"YouTube token not found in youtube_token_store")
            logger.info(f"Available YouTube user IDs: {list(youtube_token_store.keys())}")

            # Use the login user ID for the YouTube token
            youtube_user_id = user_id
            logger.info(f"Adding YouTube token to store for user: {youtube_user_id}")
            youtube_token_store[youtube_user_id] = {
                "access_token": youtube_token,
                "refresh_token": youtube_refresh_token,
                "expires_at": datetime.now() + timedelta(hours=1)
            }

        # Ensure the tokens belong to the same user
        if user_id != youtube_user_id:
            logger.warning(f"User ID mismatch: login={user_id}, youtube={youtube_user_id}")
            # Instead of failing, update the YouTube token to use the login user ID
            logger.info(f"Updating YouTube token to use login user ID: {user_id}")
            youtube_token_store[user_id] = youtube_token_store[youtube_user_id]
            if youtube_user_id != user_id:
                del youtube_token_store[youtube_user_id]
            youtube_user_id = user_id

        # Try to upload with the regular method first
        try:
            result = await upload_to_youtube(user_id, file_path, title, description)
            logger.info(f"User {user_id} uploaded video to YouTube: {result['video_id']}")
            return result
        except Exception as e:
            # If regular upload fails, try direct upload as fallback
            logger.warning(f"Regular upload failed: {str(e)}. Trying direct upload...")

            # Get tokens from token store
            youtube_access_token = youtube_token_store[user_id]["access_token"]
            youtube_refresh_token = youtube_token_store[user_id].get("refresh_token")

            # Try direct upload
            result = await upload_with_direct_credentials(
                file_path=file_path,
                title=title,
                description=description,
                access_token=youtube_access_token,
                refresh_token=youtube_refresh_token,
                client_id=config.YOUTUBE_CLIENT_ID or config.GOOGLE_CLIENT_ID,
                client_secret=config.YOUTUBE_CLIENT_SECRET or config.GOOGLE_CLIENT_SECRET
            )
            logger.info(f"User {user_id} uploaded video to YouTube using direct method: {result['video_id']}")
            return result
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
async def logout(user=Depends(get_current_user)):
    """Log out the user by removing their tokens from both stores."""
    user_id = user["sub"]
    if user_id in login_token_store:
        del login_token_store[user_id]
        logger.info(f"User {user_id} logged out from general authentication")
    if user_id in youtube_token_store:
        del youtube_token_store[user_id]
        logger.info(f"User {user_id} logged out from YouTube authorization")
    return {"message": "Logged out successfully"}


@router.get("/videos/downloaded", response_model=VideoListResponseDTO, dependencies=[Depends(get_current_user)])
async def list_downloaded_videos(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", regex="^(created_at|filename|size_bytes)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    user=Depends(get_current_user)
):
    """List all downloaded TikTok videos with pagination and sorting.

    Args:
        limit: Maximum number of videos to return (1-100)
        offset: Number of videos to skip for pagination
        sort_by: Field to sort by (created_at, filename, size_bytes)
        sort_order: Sort order (asc, desc)
        user: Authenticated user info

    Returns:
        VideoListResponseDTO: List of downloaded videos with metadata
    """
    try:
        logger.info(f"User {user['sub']} requested list of downloaded videos")
        result = await get_downloaded_videos(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return VideoListResponseDTO(**result)
    except Exception as e:
        logger.error(f"Failed to list downloaded videos for user {user['sub']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list videos: {str(e)}")


@router.get("/videos/converted", response_model=VideoListResponseDTO, dependencies=[Depends(get_current_user)])
async def list_converted_videos(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", regex="^(created_at|filename|size_bytes)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    user=Depends(get_current_user)
):
    """List all converted videos with pagination and sorting.

    Args:
        limit: Maximum number of videos to return (1-100)
        offset: Number of videos to skip for pagination
        sort_by: Field to sort by (created_at, filename, size_bytes)
        sort_order: Sort order (asc, desc)
        user: Authenticated user info

    Returns:
        VideoListResponseDTO: List of converted videos with metadata
    """
    try:
        logger.info(f"User {user['sub']} requested list of converted videos")
        result = await get_converted_videos(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return VideoListResponseDTO(**result)
    except Exception as e:
        logger.error(f"Failed to list converted videos for user {user['sub']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list videos: {str(e)}")

@router.get("/videos/stream/{filename}")
async def stream_video(filename: str):
    """Stream a video file from either the converted or downloads directory.
    
    Args:
        filename: The name of the video file to stream
        
    Returns:
        FileResponse: The video file as a stream
    """
    try:
        # Get the base directory of the project
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Check both directories with absolute paths
        converted_path = os.path.join(base_dir, "converted", filename)
        downloaded_path = os.path.join(base_dir, "downloads", filename)
        
        # Check if file exists in either directory
        if os.path.exists(converted_path):
            file_path = converted_path
        elif os.path.exists(downloaded_path):
            file_path = downloaded_path
        else:
            logger.error(f"Video not found: {filename}. Checked paths: {converted_path}, {downloaded_path}")
            raise HTTPException(status_code=404, detail="Video not found")
            
        # Return the file as a stream
        return FileResponse(
            path=file_path,
            media_type="video/mp4",
            filename=filename
        )
    except Exception as e:
        logger.error(f"Error streaming video {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/videos/delete")
async def delete_video(
    file_path: str = Body(...),
    type: str = Body(...),
    user=Depends(get_current_user)
):
    """Delete a video file.

    Args:
        file_path (str): Path to the video file
        type (str): Type of video ('downloaded' or 'converted')
        user: Authenticated user info

    Returns:
        dict: Success status and message
    """
    try:
        # Validate type
        if type not in ['downloaded', 'converted']:
            raise HTTPException(status_code=400, detail="Invalid video type")

        # Get the base directory based on type
        base_dir = 'downloads' if type == 'downloaded' else 'converted'
        
        # Get the filename from the path and construct full path
        filename = os.path.basename(file_path)
        full_path = os.path.join(base_dir, filename)

        # Check if file exists
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Video file not found")

        # Delete the file
        os.remove(full_path)
        logger.info(f"User {user['sub']} deleted video: {full_path}")

        return {
            "success": True,
            "message": "Video deleted successfully"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to delete video for user {user['sub']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete video: {str(e)}")
