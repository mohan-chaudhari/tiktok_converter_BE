import os
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.downloader import download_tiktok_video
from src.services.converter import convert_video_for_youtube
from src.config.settings import config

# Sample test data
TEST_TIKTOK_URL = "https://www.tiktok.com/@test/video/123456789"
TEST_INPUT_PATH = "./downloads/tiktok_test.mp4"
TEST_OUTPUT_PATH = "./converted/converted_tiktok_test.mp4"

@pytest.mark.asyncio
async def test_download_tiktok_video_success(tmp_path):
    """Test successful TikTok video download"""
    # Mock aiohttp response for TikTok API
    mock_api_response = {
        "code": 0,
        "data": {
            "play": "https://example.com/video.mp4",
            "title": "Test Video"
        }
    }
    mock_video_content = b"fake video content"

    # Mock aiohttp.ClientSession
    with patch("aiohttp.ClientSession.get") as mock_get:
        # Mock API call
        api_response = AsyncMock()
        api_response.json.return_value = mock_api_response
        # Mock video download
        video_response = AsyncMock()
        video_response.status = 200
        video_response.read.return_value = mock_video_content

        mock_get.side_effect = [api_response, video_response]

        # Use tmp_path as output folder
        output_folder = str(tmp_path)
        result = await download_tiktok_video(TEST_TIKTOK_URL, output_folder)

        # Assertions
        assert result["success"] is True
        assert result["message"] == "Video downloaded successfully"
        assert os.path.exists(result["file_path"])
        assert result["filename"].startswith("tiktok_")
        assert result["video_info"]["title"] == "Test Video"

@pytest.mark.asyncio
async def test_download_tiktok_video_invalid_url():
    """Test download with invalid URL"""
    with pytest.raises(ValueError, match="Invalid URL provided"):
        await download_tiktok_video("")

@pytest.mark.asyncio
async def test_download_tiktok_video_api_failure(tmp_path):
    """Test download when TikTok API fails"""
    # Mock aiohttp response with error
    mock_api_response = {"code": -1, "msg": "Invalid URL"}

    with patch("aiohttp.ClientSession.get") as mock_get:
        api_response = AsyncMock()
        api_response.json.return_value = mock_api_response
        mock_get.return_value = api_response

        output_folder = str(tmp_path)
        with pytest.raises(Exception, match="Download failed: Invalid URL"):
            await download_tiktok_video(TEST_TIKTOK_URL, output_folder)

@pytest.mark.asyncio
async def test_convert_video_for_youtube_success(tmp_path):
    """Test successful video conversion"""
    # Mock ffmpeg-python
    with patch("ffmpeg.input") as mock_input, patch("ffmpeg.output") as mock_output, \
         patch("ffmpeg.run") as mock_run:
        mock_stream = MagicMock()
        mock_input.return_value = mock_stream
        mock_output.return_value = mock_stream
        mock_run.return_value = None  # Simulate successful run

        # Use tmp_path for input/output
        input_path = str(tmp_path / "tiktok_test.mp4")
        output_folder = str(tmp_path / "converted")

        # Create a dummy input file
        with open(input_path, "wb") as f:
            f.write(b"fake video content")

        result = await convert_video_for_youtube(input_path, output_folder, "standard")

        # Assertions
        assert result["success"] is True
        assert result["message"] == "Video converted successfully"
        assert result["input_path"] == input_path
        assert result["output_path"].startswith(output_folder)
        assert result["output_name"].startswith("converted_tiktok_test")

@pytest.mark.asyncio
async def test_convert_video_for_youtube_invalid_input():
    """Test conversion with invalid input path"""
    with pytest.raises(ValueError, match="Input path must be a valid string"):
        await convert_video_for_youtube("")

@pytest.mark.asyncio
async def test_convert_video_for_youtube_ffmpeg_failure(tmp_path):
    """Test conversion when FFmpeg fails"""
    with patch("ffmpeg.input") as mock_input, patch("ffmpeg.output") as mock_output, \
         patch("ffmpeg.run") as mock_run:
        mock_stream = MagicMock()
        mock_input.return_value = mock_stream
        mock_output.return_value = mock_stream

        # Simulate FFmpeg error
        ffmpeg_error = ffmpeg.Error("ffmpeg", "error output", "error: something went wrong")
        mock_run.side_effect = ffmpeg_error

        input_path = str(tmp_path / "tiktok_test.mp4")
        output_folder = str(tmp_path / "converted")

        with open(input_path, "wb") as f:
            f.write(b"fake video content")

        with pytest.raises(Exception, match="Video conversion failed: error: something went wrong"):
            await convert_video_for_youtube(input_path, output_folder, "standard")

if __name__ == "__main__":
    pytest.main(["-v"])