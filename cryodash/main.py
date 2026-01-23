"""FastAPI application factory and main entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from cryodash.api.routes import router
from cryodash.config import APP_DESCRIPTION, APP_TITLE, APP_VERSION
from cryodash.database import init_db
from cryodash.scripts.sync_remote_logs import sync_logs

logger = logging.getLogger(__name__)

# Paths
STATIC_DIR = Path(__file__).parent / "static"

# Global scheduler
scheduler = AsyncIOScheduler()


async def sync_logs_task():
    """Async wrapper for log synchronization task."""
    try:
        logger.info("Starting scheduled log synchronization...")
        sync_logs()
        logger.info("Log synchronization completed successfully")
    except Exception as e:
        logger.error(f"Error during scheduled log sync: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown events."""
    # Startup
    init_db()

    # Configure and start scheduler
    scheduler.add_job(
        sync_logs_task,
        "interval",
        hours=1,
        id="sync_remote_logs",
        name="Sync remote cryogenic logs",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Log synchronization scheduler started (interval: 1 hour)")

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Log synchronization scheduler stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        lifespan=lifespan,
    )

    # Include API routes
    app.include_router(router)

    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Root endpoint serves index.html
    @app.get("/")
    async def root():
        """Serve the main dashboard page."""
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"message": "Welcome to CryoDash API"}

    return app


# Create app instance
app = create_app()


def main():
    """Run the application."""
    import uvicorn

    from cryodash.config import DEBUG, HOST, PORT

    uvicorn.run(
        "cryodash.main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info",
    )


if __name__ == "__main__":
    main()
