from pydantic import BaseModel, validator
from typing import Optional
from enum import Enum as PyEnum
import os

class QualityPreset(str, PyEnum):
    HIGH = "high"
    STANDARD = "standard"
    ULTRAHD = "ultrahd"
    LIVE = "live"
    TIKTOK_TO_YOUTUBE_16_9 = "tiktokToYouTube16_9"
    TIKTOK_TO_YOUTUBE_16_9_BLUR = "tiktokToYouTube16_9Blur"
    TIKTOK_TO_YOUTUBE_SIMPLE = "tiktokToYouTubeSimple"
    TIKTOK_TO_YOUTUBE_COLOR_BORDER = "tiktokToYouTubeColorBorder"
    TIKTOK_TO_YOUTUBE_HIGH_PERFORMANCE = "tiktokToYouTubeHighPerformance"
    TIKTOK_TO_YOUTUBE_SUBTITLE = "tiktokToYouTubeSubtitle"
    TIKTOK_TO_YOUTUBE_720P = "tiktokTo720p"

class ConvertRequestDTO(BaseModel):
    input_path: str
    output_folder: Optional[str] = None
    quality: Optional[QualityPreset] = QualityPreset.STANDARD

    @validator("input_path")
    def validate_input_path(cls, v):
        """Ensure input_path is a valid, existing file path"""
        if not isinstance(v, str):
            raise ValueError("Input path must be a string")
        v = os.path.abspath(v)
        if ".." in v or not os.path.isabs(v):
            raise ValueError("Invalid input path: directory traversal not allowed")
        if not os.path.isfile(v):
            raise ValueError(f"Input file does not exist: {v}")
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

class ConvertResponseDTO(BaseModel):
    success: bool
    message: str
    input_path: str
    output_path: str
    output_name: str

    class Config:
        from_attributes = True