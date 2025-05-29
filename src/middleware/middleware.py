from fastapi import Request
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler  # Fixed underscore notation
from src.config.settings import logger

def setup_middleware(app):
    """Configure all middleware for the FastAPI app"""
    # Rate limiting
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting enabled: configured in routes")
    
    # CORS - UNCOMMENTED AND CONFIGURED
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For development - change to specific origins in production
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods during development
        allow_headers=["*"],  # Allow all headers during development
        expose_headers=["Location"],  # Important for redirects to work properly
    )
    logger.info("CORS middleware enabled with development settings")
    
    # Security headers - can be re-enabled later
    # async def add_security_headers(request: Request, call_next):
    #     # Exclude specific routes from the security headers middleware
    #     if request.url.path in ["/docs", "/openapi.json", "/redoc"]:
    #         response = await call_next(request)
    #         return response
    #         
    #     response = await call_next(request)
    #     response.headers["X-Content-Type-Options"] = "nosniff"
    #     response.headers["X-Frame-Options"] = "DENY"
    #     response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'"
    #     response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    #     return response
    # app.middleware("http")(add_security_headers)
    logger.info("Security headers middleware configured but disabled")
