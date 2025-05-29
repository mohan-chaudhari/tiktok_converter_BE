"""
Direct YouTube API implementation without using the token store.
This is a fallback solution when the regular approach fails.
"""

import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
import httplib2
from src.config.settings import logger, config

async def upload_with_direct_credentials(
    file_path: str,
    title: str,
    description: str = "",
    access_token: str = None,
    refresh_token: str = None,
    client_id: str = None,  # Optional, will use config if not provided
    client_secret: str = None  # Optional, will use config if not provided
):
    """
    Upload a video to YouTube using directly provided credentials.
    This bypasses the token store and creates credentials directly.
    """
    try:
        # Validate inputs
        if not file_path:
            raise ValueError("File path is required")
        if not title:
            raise ValueError("Video title is required")
        if not access_token:
            raise ValueError("Access token is required")
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Video file not found: {file_path}")

        # Always use environment variables for client credentials
        client_id = config.YOUTUBE_CLIENT_ID or config.GOOGLE_CLIENT_ID
        client_secret = config.YOUTUBE_CLIENT_SECRET or config.GOOGLE_CLIENT_SECRET

        if not client_id or not client_secret:
            raise ValueError("Client ID and Client Secret are not configured in environment variables.")

        # Log credential info (masked)
        masked_token = access_token[:4] + "****" + access_token[-4:] if len(access_token) > 8 else "****"
        masked_client_id = client_id[:4] + "****" + client_id[-4:] if len(client_id) > 8 else "****"
        masked_client_secret = client_secret[:4] + "****" + client_secret[-4:] if len(client_secret) > 8 else "****"

        logger.info(f"Direct upload with: token={masked_token}, client_id={masked_client_id}, client_secret={masked_client_secret}")

        if refresh_token:
            masked_refresh = refresh_token[:4] + "****" + refresh_token[-4:] if len(refresh_token) > 8 else "****"
            logger.info(f"Refresh token provided: {masked_refresh}")
        else:
            logger.warning("No refresh token provided. Token refresh will not be possible.")

        # Create credentials object with all required fields
        logger.info("Creating credentials directly")

        # Dump all credential info for debugging
        cred_info = {
            "token": masked_token,
            "refresh_token": masked_refresh if refresh_token else None,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": masked_client_id,
            "client_secret": masked_client_secret,
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"]
        }
        logger.info(f"Credential info: {json.dumps(cred_info, indent=2)}")

        # Create the credentials object
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/youtube.upload"]
        )

        # Create an authorized HTTP object
        logger.info("Creating authorized HTTP object")
        http = httplib2.Http()
        authorized_http = AuthorizedHttp(credentials, http=http)

        # Build the YouTube API client with the authorized HTTP object
        logger.info("Initializing YouTube API client")
        youtube = build("youtube", "v3", http=authorized_http, static_discovery=False, cache_discovery=False)

        # Prepare the video upload
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
        logger.info("Executing YouTube upload request")
        response = request.execute()

        if not response or "id" not in response:
            raise ValueError("YouTube API returned an invalid response")

        video_id = response["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        logger.info(f"Successfully uploaded video to YouTube: {video_id}")
        return {
            "success": True,
            "video_id": video_id,
            "url": video_url,
            "title": title,
            "privacy": "private"
        }
    except HttpError as he:
        error_content = he.content.decode() if hasattr(he, 'content') else str(he)
        logger.error(f"YouTube API error: {error_content}")
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
        logger.error(f"Failed to upload to YouTube: {str(e)}")
        logger.error(f"Traceback: {error_traceback}")
        raise ValueError(f"YouTube upload failed: {str(e)}")
