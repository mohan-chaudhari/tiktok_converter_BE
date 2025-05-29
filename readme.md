# TikTok Converter

A secure and robust FastAPI-based application for downloading TikTok videos and converting them into YouTube-compatible formats.

## Features

- **Download TikTok Videos**: Fetch videos asynchronously using the TikTok API (`tikwm.com`).
- **Convert Videos**: Transform videos into YouTube-friendly formats with customizable quality presets.
- **Security**: Includes input validation, rate limiting, API key authentication, and secure file handling.
- **Robustness**: Comprehensive error handling and logging for reliability.

## Project Structure - 

```

tiktok_converter/
├── src/
│ ├── api/ # API routes
│ ├── services/ # Download and conversion logic
│ ├── utils/ # Helpers and security utilities
│ ├── config/ # Configuration settings
│ └── middleware/ # Rate limiting middleware
├── tests/ # Unit tests
├── .env # Environment variables
├── .gitignore # Git ignore file
├── requirements.txt # Python dependencies
└── main.py # Entry point

```

## Prerequisites

- Python 3.11+
- FFmpeg installed (`brew install ffmpeg` on macOS, `sudo apt install ffmpeg` on Linux, or download for Windows)

## Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/tiktok_converter.git
   cd tiktok_converter
   ```

````

2. **Create a Virtual Environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the root directory:
   ```
   PORT=3000
   TIKTOK_API_BASE=https://www.tikwm.com/api/
   DOWNLOAD_FOLDER=./downloads
   CONVERTED_FOLDER=./converted
   ENV=development
   API_KEY=your-secret-api-key-here  # Generate a strong key
   LOG_LEVEL=INFO
   ```

## Usage

1. **Run the Application**:

   ```bash
   python main.py
   ```

   The API will be available at `http://localhost:3000`.

2. **API Endpoints**:
   - **Download TikTok Video**:
     - `POST /api/download`
     - Headers: `X-API-Key: your-secret-api-key-here`
     - Body:
       ```json
       {
         "url": "https://www.tiktok.com/@user/video/123456789",
         "output_folder": "./downloads"
       }
       ```
   - **Convert Video for YouTube**:
     - `POST /api/convert`
     - Headers: `X-API-Key: your-secret-api-key-here`
     - Body:
       ```json
       {
         "input_path": "./downloads/tiktok_1634567890123.mp4",
         "output_folder": "./converted",
         "quality": "standard"
       }
       ```
   - Use Swagger UI at `http://localhost:3000/docs` for interactive testing.

## Security Features

- **Input Validation**: Prevents injection and traversal attacks (e.g., sanitizes URLs and filenames).
- **Rate Limiting**: Limits to 100 requests/minute per IP to mitigate DoS attacks.
- **Authentication**: Requires an API key (`X-API-Key`) for all requests.
- **Secure File Handling**: Uses absolute paths and cleanup to prevent exploits.
- **Logging**: Logs errors securely without exposing sensitive details.

## Testing

1. **Install Test Dependencies**:
   Ensure `pytest` and `pytest-asyncio` are installed (included in `requirements.txt`).

2. **Run Tests**:
   ```bash
   pytest tests/test_services.py -v
   ```
   Tests cover:
   - Successful downloads and conversions
   - Input validation failures
   - Error handling (e.g., API or FFmpeg failures)
   - Security utilities

## Example Commands

- Download a video:
  ```bash
  curl -X POST "http://localhost:3000/api/download" \
       -H "X-API-Key: your-secret-api-key-here" \
       -H "Content-Type: application/json" \
       -d '{"url": "https://www.tiktok.com/@user/video/123456789"}'
  ```
- Convert a video:
  ```bash
  curl -X POST "http://localhost:3000/api/convert" \
       -H "X-API-Key: your-secret-api-key-here" \
       -H "Content-Type: application/json" \
       -d '{"input_path": "./downloads/tiktok_1634567890123.mp4", "quality": "standard"}'
  ```

## Troubleshooting

- **SSL Errors**: Update `certifi` (`pip install --upgrade certifi`) or check your system’s CA certificates.
- **FFmpeg Errors**: Ensure FFmpeg is installed and accessible in your PATH.
- **API Key Issues**: Verify the `X-API-Key` header matches the `.env` value.

## Contributing

Feel free to submit issues or PRs to enhance functionality or security.

## License

MIT License - see `LICENSE` file (add one if desired).

```

---
```
````
