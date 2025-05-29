from pydantic import BaseModel
from typing import List, Optional
import os
from datetime import datetime


class VideoFileDTO(BaseModel):
    """DTO for a single video file"""
    filename: str
    file_path: str
    size_bytes: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class VideoListResponseDTO(BaseModel):
    """DTO for a list of video files"""
    videos: List[VideoFileDTO]
    total_count: int
    folder_path: str
    
    class Config:
        from_attributes = True


class VideoFilterParams(BaseModel):
    """Query parameters for filtering videos"""
    limit: Optional[int] = 50
    offset: Optional[int] = 0
    sort_by: Optional[str] = "created_at"  # Options: created_at, filename, size_bytes
    sort_order: Optional[str] = "desc"  # Options: asc, desc
    
    class Config:
        from_attributes = True
