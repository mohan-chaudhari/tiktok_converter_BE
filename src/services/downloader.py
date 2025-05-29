import aiohttp
import aiofiles
import os
import ssl
import certifi
from src.config.settings import config
from src.utils.helpers import generate_filename

async def download_tiktok_video(url: str, output_folder: str = None) -> dict:
    if not url or not isinstance(url, str):
        raise ValueError("Invalid URL provided")

    output_folder = output_folder or config.DOWNLOAD_FOLDER
    if not output_folder or not isinstance(output_folder, str):
        raise ValueError("Output folder must be a valid string path")

    os.makedirs(output_folder, exist_ok=True)
    filename = generate_filename()
    file_path = os.path.join(output_folder, filename)

    # Create SSL context with certifi's CA bundle
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    async with aiohttp.ClientSession() as session:
        api_url = f"{config.TIKTOK_API_BASE}?url={url}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        try:
            async with session.get(api_url, headers=headers, timeout=10, ssl=ssl_context) as response:
                data = await response.json()
                if data.get("code") != 0 or not data.get("data", {}).get("play"):
                    raise Exception(data.get("msg", "Failed to get valid video URL"))
                video_url = data["data"]["play"]

            async with session.get(video_url, headers=headers, timeout=30, ssl=ssl_context) as video_response:
                if video_response.status != 200:
                    raise Exception(f"Failed to download video: Status {video_response.status}")
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(await video_response.read())

            return {
                "success": True,
                "message": "Video downloaded successfully",
                "file_path": file_path,
                "filename": filename,
                "video_info": data["data"]
            }
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise Exception(f"Download failed: {str(e)}")