import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
import httplib2
from src.config.settings import logger, config
from src.auth.oauth import youtube_token_store

async def create_youtube_client(user_id: str):
    """Create a YouTube API client with proper credentials."""
    # Check if user has a token
    if user_id not in youtube_token_store:
        logger.warning(f"No YouTube token found for user {user_id} in token store")
        logger.info(f"Available user IDs in YouTube token store: {list(youtube_token_store.keys())}")

        # Try to find a token for this user by checking all tokens
        for uid, token_data in youtube_token_store.items():
            logger.info(f"Checking token for user {uid}")
            # If we find a matching user ID in any part of the token data, use it
            if str(uid).lower() == str(user_id).lower() or \
               (isinstance(token_data, dict) and \
                any(str(user_id).lower() in str(v).lower() for v in token_data.values() if v)):
                logger.info(f"Found potential match: {uid}")
                user_id = uid
                break

        # If still not found, raise error
        if user_id not in youtube_token_store:
            raise ValueError(f"No YouTube token found for user {user_id}")

    # Get access token and refresh token
    token_data = youtube_token_store[user_id]
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    if not access_token:
        raise ValueError("YouTube access token is missing or invalid")

    # Log token info (masked)
    masked_token = access_token[:4] + "****" + access_token[-4:] if len(access_token) > 8 else "****"
    logger.info(f"Using YouTube token: {masked_token} for user: {user_id}")

    # Log refresh token status
    if refresh_token:
        masked_refresh = refresh_token[:4] + "****" + refresh_token[-4:] if len(refresh_token) > 8 else "****"
        logger.info(f"Refresh token available: {masked_refresh}")
    else:
        logger.warning("No refresh token available. Token refresh will not be possible.")

    # Create credentials object with all required fields
    logger.info(f"Creating credentials for user {user_id}")
    credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.YOUTUBE_CLIENT_ID or config.GOOGLE_CLIENT_ID,
        client_secret=config.YOUTUBE_CLIENT_SECRET or config.GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )

    # Create an authorized HTTP object
    logger.info(f"Creating authorized HTTP object")
    http = httplib2.Http()
    authorized_http = AuthorizedHttp(credentials, http=http)

    # Build the YouTube API client with the authorized HTTP object
    logger.info(f"Initializing YouTube API client for user {user_id}")
    youtube = build("youtube", "v3", http=authorized_http, static_discovery=False, cache_discovery=False)

    return youtube


async def upload_to_youtube(user_id: str, file_path: str, title: str, description: str = ""):
    """Upload a video to YouTube using the user's access token."""
    try:
        # Validate inputs
        if not user_id:
            raise ValueError("User ID is required")
        if not file_path:
            raise ValueError("File path is required")
        if not title:
            raise ValueError("Video title is required")

        # Check if file exists
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Video file not found: {file_path}")

        # Create YouTube client
        youtube = await create_youtube_client(user_id)

        body = {
            "snippet": {
                "title": title,
                "description": description or "Uploaded via TikTok Converter",
                "tags": ["tiktok", "converted"],
                "categoryId": "22",  # People & Blogs
            },
            "status": {
                "privacyStatus": "private",  # Can be "public", "unlisted", or "private"
            },
        }

        # Get file size for logging
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
        logger.info(f"Uploading video file: {file_path} ({file_size:.2f} MB)")

        # Create media upload object
        media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)

        # Create upload request
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        # Execute the request
        logger.info(f"Executing YouTube upload request for user {user_id}")
        response = request.execute()

        if not response or "id" not in response:
            raise ValueError("YouTube API returned an invalid response")

        video_id = response["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        logger.info(f"Successfully uploaded video to YouTube for user {user_id}: {video_id}")
        return {
            "success": True,
            "video_id": video_id,
            "url": video_url,
            "title": title,
            "privacy": "private"
        }
    except HttpError as he:
        error_content = he.content.decode() if hasattr(he, 'content') else str(he)
        logger.error(f"YouTube API error for user {user_id}: {error_content}")
        raise ValueError(f"YouTube API error: {error_content}")
    except FileNotFoundError as fnf:
        logger.error(f"File not found: {str(fnf)}")
        raise
    except ImportError as ie:
        logger.error(f"Import error: {str(ie)}. Make sure all dependencies are installed.")
        logger.info("Run './install_dependencies.sh' to install required packages")
        raise ValueError(f"Missing dependency: {str(ie)}. Run './install_dependencies.sh' to install required packages.")
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Failed to upload to YouTube for user {user_id}: {str(e)}")
        logger.error(f"Traceback: {error_traceback}")
        raise ValueError(f"YouTube upload failed: {str(e)}")