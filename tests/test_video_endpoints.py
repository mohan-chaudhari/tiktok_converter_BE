import os
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime
from main import app

client = TestClient(app)

# Mock authentication for tests
@pytest.fixture(autouse=True)
def mock_auth():
    with patch("src.auth.guards.get_current_user", return_value={"sub": "test_user_id", "email": "test@example.com"}):
        yield


@pytest.fixture
def mock_video_files():
    return {
        "videos": [
            {
                "filename": "tiktok_123456789.mp4",
                "file_path": "/path/to/downloads/tiktok_123456789.mp4",
                "size_bytes": 1024000,
                "created_at": datetime.now()
            },
            {
                "filename": "tiktok_987654321.mp4",
                "file_path": "/path/to/downloads/tiktok_987654321.mp4",
                "size_bytes": 2048000,
                "created_at": datetime.now()
            }
        ],
        "total_count": 2,
        "folder_path": "/path/to/downloads"
    }


def test_list_downloaded_videos(mock_video_files):
    """Test listing downloaded videos endpoint"""
    with patch("src.services.file_service.get_downloaded_videos", return_value=mock_video_files):
        response = client.get("/videos/downloaded")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        assert len(data["videos"]) == 2
        assert data["total_count"] == 2
        assert "folder_path" in data


def test_list_converted_videos(mock_video_files):
    """Test listing converted videos endpoint"""
    with patch("src.services.file_service.get_converted_videos", return_value=mock_video_files):
        response = client.get("/videos/converted")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        assert len(data["videos"]) == 2
        assert data["total_count"] == 2
        assert "folder_path" in data


def test_list_videos_with_pagination():
    """Test pagination parameters for video listing"""
    mock_data = {
        "videos": [{"filename": "test.mp4", "file_path": "/path/test.mp4", "size_bytes": 1000, "created_at": datetime.now()}],
        "total_count": 1,
        "folder_path": "/path"
    }
    
    with patch("src.services.file_service.get_downloaded_videos", return_value=mock_data):
        response = client.get("/videos/downloaded?limit=10&offset=0&sort_by=filename&sort_order=asc")
        assert response.status_code == 200
        # Verify that the parameters were passed correctly (would need to check the mock was called with these params)


def test_list_videos_with_invalid_params():
    """Test validation of query parameters"""
    response = client.get("/videos/downloaded?limit=1000")  # Exceeds max limit
    assert response.status_code == 422  # Validation error
    
    response = client.get("/videos/downloaded?sort_by=invalid_field")  # Invalid sort field
    assert response.status_code == 422  # Validation error
