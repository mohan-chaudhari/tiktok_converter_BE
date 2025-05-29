from pydantic import BaseModel, validator
from typing import Optional
import re
import os

class DownloadRequestDTO(BaseModel):
    url: str
    output_folder: Optional[str] = None

    @validator("url")
    def validate_url(cls, v):
        """Ensure the URL is a valid TikTok video URL"""
        if not re.match(r"^https?://(www\.)?tiktok\.com/@[^/]+/video/\d+(\?.*)?$", v):
            raise ValueError("Invalid TikTok URL format. Expected: https://www.tiktok.com/@user/video/123456789")
        return v

    @validator("output_folder", pre=True)
    def validate_output_folder(cls, v):
        """Ensure output_folder is a valid, safe directory path if provided"""
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("Output folder must be a string")
        if ".." in v or v.startswith("/") or v.startswith("\\"):
            raise ValueError("Invalid output folder path: directory traversal not allowed")
        return os.path.abspath(v)

class DownloadResponseDTO(BaseModel):
    success: bool
    message: str
    file_path: str
    filename: str
    video_info: dict

    class Config:
        from_attributes = True