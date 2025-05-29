import os
import ffmpeg
from src.config.settings import config
from src.utils.helpers import generate_converted_filename

async def convert_video_for_youtube(
    input_path: str,
    output_folder: str = config.CONVERTED_FOLDER,
    quality: str = None,  # Accepts None, will default to "standard"
) -> dict:
    """
    Converts video to YouTube-compatible format
    """

    if not input_path or not isinstance(input_path, str):
        raise ValueError("Input path must be a valid string")

    output_folder = output_folder or config.CONVERTED_FOLDER
    os.makedirs(output_folder, exist_ok=True)
    
    output_path = os.path.join(output_folder, generate_converted_filename(input_path))

    youtube_presets = {
         "high": {
            "videoCodec": "libx264",
            "audioCodec": "aac",
             "ar": "44100",
            "outputOptions": [
                "-movflags", "faststart",
                "-profile:v", "high",
                "-preset", "slower",
                "-bf", "2",
                "-g", "30",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=-1:1080",
                "-b:a", "192k",
                # "-ar", "48000",
                "-maxrate", "8M",
                "-bufsize", "16M",
                "-threads", "0",
            ],
        },
        "standard": {
            "videoCodec": "libx264",
            "audioCodec": "aac",
            "ar": "44100",  # ✅ Pass as string (FFmpeg requirement)
            "outputOptions": [
                "-movflags", "faststart",
                "-profile:v", "main",
                "-preset", "fast",
                "-g", "30",
                "-crf", "26",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=-1:480",
                "-b:a", "96k",
                "-maxrate", "2.5M",
                "-bufsize", "5M",
                "-threads", "0",
            ],
        },
        "ultraHD": {
            "videoCodec": "libx264",
            "audioCodec": "aac",
            "ar": "48000",
            "outputOptions": [
                "-movflags", "faststart",
                "-profile:v", "high",
                "-preset", "slower",
                "-bf", "2",
                "-g", "30",
                "-crf", "16",
                "-pix_fmt", "yuv420p",
                # Fix the scaling to ensure width is always even
                "-vf", "scale=trunc(oh*a/2)*2:2160",
                "-b:a", "320k",
                "-maxrate", "25M",
                "-bufsize", "50M",
                "-threads", "0",
            ],
        },
        "live": {
            "videoCodec": "libx264",
            "audioCodec": "aac",
            "ar": "44100",
            "outputOptions": [
                "-movflags", "faststart",
                "-profile:v", "main",
                "-preset", "veryfast",
                "-g", "60",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=-1:720",
                "-b:a", "128k",
                # "-ar", "44100",
                "-maxrate", "4M",
                "-bufsize", "8M",
                "-x264opts", "scenecut=0:bframes=0",
                "-threads", "4",
            ],
        },
        "tiktokToYouTube16_9": {
            "videoCodec": "libx264",
            "audioCodec": "aac",
            "ar": "44100",
            "outputOptions": [
                "-movflags", "faststart",
                "-profile:v", "high",
                "-preset", "medium",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-vf", "pad=max(iw\\,ih*(16/9)):ih:(ow-iw)/2:0:black",
                "-b:a", "128k",
                # "-ar", "48000",
            ],
        },
        "tiktokToYouTube16_9Blur": {
            "videoCodec": "libx264",
            "audioCodec": "aac",
            "ar": "44100",
            "outputOptions": [
                "-movflags", "faststart",
                "-profile:v", "high",
                "-preset", "medium",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-vf", "split[original][copy];[copy]scale=1920:1080,boxblur=20:5[blurred];[blurred][original]overlay=(W-w)/2:(H-h)/2,setsar=1",
                "-b:a", "128k"
            ],
            "outputWidth": 1920,
            "outputHeight": 1080
        },
        "tiktokToYouTubeSimple": {
            "videoCodec": "libx264",
            "audioCodec": "aac",
            "ar": "44100",
            "outputOptions": [
                "-movflags", "faststart",
                "-profile:v", "high",
                "-preset", "medium",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=-1:1080,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
                "-b:a", "128k",
                # "-ar", "48000",
            ],
        },
        "tiktokToYouTubeColorBorder": {
            "videoCodec": "libx264",
            "audioCodec": "aac",
            "ar": "48000",
            "outputOptions": [
                "-movflags", "faststart",
                "-profile:v", "high",
                "-preset", "medium",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-vf", "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:pink",
                "-b:a", "128k",
                # "-ar", "48000",
            ],
        },
        "tiktokTo720p": {
            "videoCodec": "libx264",
            "audioCodec": "aac",
            "ar": "44100",
            "outputOptions": [
                "-movflags", "faststart",
                "-profile:v", "main",
                "-preset", "fast",
                "-crf", "22",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=-1:720,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black",
                "-b:a", "128k",
                # "-ar", "48000",
            ],
        },
        "tiktokToYouTubeSubtitle": {
            "videoCodec": "libx264",
            "audioCodec": "aac",
            "ar": "44100",
            "outputOptions": [
                "-movflags", "faststart",
                "-profile:v", "high",
                "-preset", "medium",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=-1:1080,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
                "-b:a", "128k",
                # "-ar", "48000",
                "-c:s", "mov_text",
            ],
        },
        "tiktokToYouTubeHighPerformance": {
            "videoCodec": "libx264",
            "audioCodec": "aac",
            "ar": "44100",
            "outputOptions": [
                "-movflags", "faststart",
                "-profile:v", "high",
                "-preset", "ultrafast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=-1:1080,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
                "-b:a", "128k",
                # "-ar", "48000",
                "-tune", "zerolatency",
                "-threads", "8",
            ],
        },
    }

    # ✅ Ensure valid quality preset is always used
    quality = quality or "standard"
    preset = youtube_presets.get(quality)
    if not preset:
        valid_presets = ", ".join(youtube_presets.keys())  # Get available preset names
        raise ValueError(f"Invalid quality preset: {quality}. Available presets: {valid_presets}")

    try:
        stream = ffmpeg.input(input_path)

        # ✅ Convert outputOptions to key-value arguments
        options_dict = {
            opt.lstrip("-"): val
            for opt, val in zip(preset["outputOptions"][::2], preset["outputOptions"][1::2])
        }

        # ✅ Apply correct FFmpeg argument passing
        stream = ffmpeg.output(
            stream,
            output_path,
            vcodec=preset["videoCodec"],
            acodec=preset["audioCodec"],
            ar=preset["ar"],  # ✅ Properly passed as a named argument
            **options_dict
        )

        ffmpeg.run(stream, overwrite_output=True, quiet=True)

        return {
            "success": True,
            "message": "Video converted successfully",
            "input_path": input_path,
            "output_path": output_path,
            "output_name": os.path.basename(output_path),
        }

    except ffmpeg.Error as e:
        error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
        raise Exception(f"Video conversion failed: {error_msg}")
    except Exception as e:
        raise Exception(f"Unexpected error during conversion: {str(e)}")
