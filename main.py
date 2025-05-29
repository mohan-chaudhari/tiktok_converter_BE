
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles  # For serving static files
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware  # Add this import
from src.api.routes import router
from src.config.settings import config, logger
from src.exceptions.handlers import (
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from src.middleware.middleware import setup_middleware
# Token stores are used in the commented-out test-cors endpoint
# from src.auth.oauth import login_token_store, youtube_token_store

app = FastAPI(
    title="TikTok Converter API",
    description="API for downloading and converting TikTok videos with Google OAuth2 SSO",
    version="1.0.0",
)

# IMPORTANT: Add CORS middleware directly here, before any routes or other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Location", "Content-Type"],
)
logger.info("CORS middleware added directly in main.py")

# Mount static files directory for youtube_auth.html
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Add SessionMiddleware with correct config key
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET)

# Setup all additional middleware (rate limiting, etc.)
setup_middleware(app)  # Keep this for other middleware

# Register global exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Include API routes
app.include_router(router, prefix="")

# Add a test endpoint to verify CORS is working and display token stores
# @app.get("/test-cors")
# def test_cors():
#     # Prepare token stores for display (remove sensitive data)
#     login_tokens = {}
#     for user_id, token_data in login_token_store.items():
#         # Create a copy with masked tokens for security
#         login_tokens[user_id] = {
#             "access_token": mask_token(token_data.get("access_token")),
#             "refresh_token": mask_token(token_data.get("refresh_token")),
#             "expires_at": str(token_data.get("expires_at")) if "expires_at" in token_data else None
#         }

#     youtube_tokens = {}
#     for user_id, token_data in youtube_token_store.items():
#         # Create a copy with masked tokens for security
#         youtube_tokens[user_id] = {
#             "access_token": mask_token(token_data.get("access_token")),
#             "refresh_token": mask_token(token_data.get("refresh_token")),
#             "expires_at": str(token_data.get("expires_at")) if "expires_at" in token_data else None
#         }

#     return {
#         "message": "CORS is working!",
#         "login_token_store": login_tokens,
#         "youtube_token_store": youtube_tokens,
#         "login_token_count": len(login_token_store),
#         "youtube_token_count": len(youtube_token_store)
#     }


# Function used in the disabled test-cors endpoint
# def mask_token(token):
#     """Mask a token for security when displaying"""
#     if not token:
#         return None
#     if len(token) <= 8:
#         return "****"
#     return token[:4] + "****" + token[-4:]


# Test endpoint disabled as requested
# @app.get("/test-cors")
# def test_cors():
#     return {"message": "CORS is working!"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="TikTok Converter API",
        version="1.0.0",
        description="API for downloading and converting TikTok videos with Google OAuth2 SSO",
        routes=app.routes,
    )

    # Add security definitions for both login and YouTube tokens
    openapi_schema["components"]["securitySchemes"] = {
        "LoginBearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your Google OAuth2 login token: Bearer <login_access_token>",
        },
        "YouTubeBearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "name": "YouTube-Authorization",
            "description": "Enter your YouTube OAuth2 token: Bearer <youtube_access_token>",
        },
    }

    # Apply security to all protected endpoints
    # Map of endpoint paths to security requirements
    protected_paths = {
        "/download": [{"LoginBearerAuth": []}],
        "/convert": [{"LoginBearerAuth": []}],
        "/user": [{"LoginBearerAuth": []}],
        "/logout": [{"LoginBearerAuth": []}],
        "/youtube/upload": [],  # No auth in path - tokens provided in body or headers
        "/youtube/auth": [{"LoginBearerAuth": []}],
        "/videos/downloaded": [{"LoginBearerAuth": []}],
        "/videos/converted": [{"LoginBearerAuth": []}]
    }

    # Test endpoint disabled
    # if "/test-cors" in openapi_schema["paths"]:
    #     openapi_schema["paths"]["/test-cors"]["get"]["description"] = "Test endpoint for CORS verification"
    #     openapi_schema["paths"]["/test-cors"]["get"]["tags"] = ["testing"]

    # Update YouTube upload endpoint descriptions
    if "/youtube/upload" in openapi_schema["paths"]:
        openapi_schema["paths"]["/youtube/upload"]["post"]["description"] = "Upload a video to YouTube. Provide tokens in body or headers."
        openapi_schema["paths"]["/youtube/upload"]["post"]["tags"] = ["youtube"]

    # Debug: Print all paths in the OpenAPI schema
    logger.info(f"Available paths in OpenAPI schema: {list(openapi_schema['paths'].keys())}")

    # Apply security requirements to each path
    for path, security in protected_paths.items():
        # Check if the path exists in the schema
        if path in openapi_schema["paths"]:
            # Apply to all methods (GET, POST, etc.)
            for method in openapi_schema["paths"][path]:
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    openapi_schema["paths"][path][method]["security"] = security
                    logger.info(f"Applied security to {method.upper()} {path}")
        else:
            logger.warning(f"Path {path} not found in OpenAPI schema")

    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Apply custom OpenAPI schema for all environments
app.openapi_schema = None  # Force refresh
app.openapi = custom_openapi
logger.info("Custom OpenAPI schema applied")

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting TikTok Converter API on port {config.PORT} in {config.ENV} mode")
    ssl_kwargs = {"ssl_keyfile": "path/to/key.pem", "ssl_certfile": "path/to/cert.pem"} if config.ENV == "production" else {}
    uvicorn.run(app, host="0.0.0.0", port=config.PORT, **ssl_kwargs)
