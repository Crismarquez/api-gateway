"""

"""

import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from app.routers import auth as auth_router


logger = logging.getLogger("default-logger")

# Create FastAPI app
app = FastAPI(
    title="Api Gateway",
    version="1.0.0",
    description="Api Gateway for the application",
    redirect_slashes=False  # Disable automatic trailing slash redirects
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Cache-Control", "Content-Type", "Connection"]
)

# Include routers
app.include_router(auth_router.router)


@app.on_event("startup")
async def startup_event():
    """
    Application startup event.

    Initializes global services:
    - Database connection (Cosmos DB)
    - Storage service
    - Logging configuration
    """
    logger.info("=" * 50)
    logger.info("Starting API Gateway")
    logger.info("=" * 50)

    # Pre-initialize services for faster first request
    try:
        print("Startup event")

    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.

    Performs cleanup:
    - Close database connections
    - Cleanup temporary resources
    """
    logger.info("=" * 50)
    logger.info("Shutting down AI Document Indexing & Knowledge Base Platform")
    logger.info("=" * 50)

    # Close database connections

    logger.info("Application shutdown complete")


@app.get("/", tags=["home"])
def message():
    """
    Root endpoint.

    Returns welcome message with API information.
    """
    return HTMLResponse("""
    <html>

    """)


if __name__ == "__main__":
    # Configure uvicorn with optimized settings
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8001,
        workers=1,  # Single worker for development (can increase for production)
        timeout_keep_alive=120,  # Increased timeout for long-running operations
        limit_concurrency=100,  # Maximum number of concurrent connections
        backlog=2048,  # Maximum number of connections to queue
        log_level="info"
    )
