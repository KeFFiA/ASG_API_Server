import time

from ..Server import app
from fastapi import Request
from fastapi.responses import JSONResponse

from ...Config import setup_logger

logger = setup_logger('fastapi_app')

# Middleware for requests logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} "
        f"completed_in={duration:.2f}s status_code={response.status_code}"
    )
    return response

# Custom exception handler
@app.exception_handler(Exception)
async def custom_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )