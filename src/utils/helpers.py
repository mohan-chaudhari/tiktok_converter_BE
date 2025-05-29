import os
import time


def generate_filename() -> str:
    """Generate unique filename with timestamp"""
    return f"tiktok_{int(time.time() * 1000)}.mp4"


def generate_converted_filename(input_path: str) -> str:
    """Generate filename for converted video"""
    base_name = os.path.basename(input_path).replace(".mp4", "")
    return f"converted_{base_name}.mp4"
