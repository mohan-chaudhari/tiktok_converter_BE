import os
import glob
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.config.settings import config, logger


async def get_video_files(folder_path: str, limit: int = 50, offset: int = 0, 
                         sort_by: str = "created_at", sort_order: str = "desc") -> Dict[str, Any]:
    """
    Get a list of video files from the specified folder with pagination and sorting.
    
    Args:
        folder_path: Path to the folder containing video files
        limit: Maximum number of files to return
        offset: Number of files to skip
        sort_by: Field to sort by (created_at, filename, size_bytes)
        sort_order: Sort order (asc, desc)
        
    Returns:
        Dictionary with videos list, total count, and folder path
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        logger.info(f"Created folder: {folder_path}")
        
    # Get all MP4 files in the folder
    video_files = glob.glob(os.path.join(folder_path, "*.mp4"))
    
    # Create a list of file info dictionaries
    file_info_list = []
    for file_path in video_files:
        try:
            stats = os.stat(file_path)
            file_info = {
                "filename": os.path.basename(file_path),
                "file_path": file_path,
                "size_bytes": stats.st_size,
                "created_at": datetime.fromtimestamp(stats.st_ctime)
            }
            file_info_list.append(file_info)
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {str(e)}")
    
    # Sort the list
    if sort_by in ["created_at", "filename", "size_bytes"]:
        reverse = sort_order.lower() == "desc"
        file_info_list.sort(key=lambda x: x[sort_by], reverse=reverse)
    
    # Apply pagination
    total_count = len(file_info_list)
    paginated_files = file_info_list[offset:offset + limit]
    
    return {
        "videos": paginated_files,
        "total_count": total_count,
        "folder_path": folder_path
    }


async def get_downloaded_videos(limit: int = 50, offset: int = 0, 
                               sort_by: str = "created_at", sort_order: str = "desc") -> Dict[str, Any]:
    """Get a list of downloaded TikTok videos"""
    return await get_video_files(
        config.DOWNLOAD_FOLDER, 
        limit=limit, 
        offset=offset, 
        sort_by=sort_by, 
        sort_order=sort_order
    )


async def get_converted_videos(limit: int = 50, offset: int = 0, 
                              sort_by: str = "created_at", sort_order: str = "desc") -> Dict[str, Any]:
    """Get a list of converted videos"""
    return await get_video_files(
        config.CONVERTED_FOLDER, 
        limit=limit, 
        offset=offset, 
        sort_by=sort_by, 
        sort_order=sort_order
    )
