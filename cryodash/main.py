"""FastAPI application factory and main entry point."""

import logging
import logging.config
import time
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter  # type: ignore
from slowapi.util import get_remote_address  # type: ignore

from cryodash.api.routes import router
from cryodash.config import APP_DESCRIPTION, APP_TITLE, APP_VERSION
from cryodash.database import init_db
from cryodash.scripts.sync_remote_logs import sync_logs

# Configure logging - reduced verbosity for DEBUG, keep pertinent INFO
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["default"],
            "level": "INFO",
            "propagate": True,
        },
        "cryodash": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "cryodash.main": {
            "handlers": ["default"],
            "level": "DEBUG",
            "propagate": False,
        },
        "cryodash.security": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["default"],
            "level": "WARNING",
            "propagate": False,
        },
        "apscheduler.scheduler": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "apscheduler.executors": {
            "handlers": ["default"],
            "level": "WARNING",
            "propagate": False,
        },
        "watchfiles": {
            "handlers": ["default"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Rate limiter for slowapi
limiter = Limiter(key_func=get_remote_address)

# Paths
STATIC_DIR = Path(__file__).parent / "static"

# Global scheduler
scheduler = AsyncIOScheduler(timezone="America/Toronto")
logger.debug("Scheduler timezone set to America/Toronto")


async def sync_logs_task():
    """Async wrapper for log synchronization task."""
    logger.debug("sync_logs_task triggered")
    try:
        logger.info("Starting scheduled log synchronization...")
        sync_logs()
        logger.debug("Scheduled log synchronization completed successfully")
        logger.info("Log synchronization completed successfully")
    except Exception as e:
        logger.error(f"Error during scheduled log sync: {e}", exc_info=True)
        logger.debug(f"Sync error details: {type(e).__name__}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown events."""
    # Startup
    logger.debug("Application startup: initializing database")
    init_db()
    logger.debug("Database initialization complete")

    # Configure and start scheduler
    logger.debug("Configuring APScheduler with sync_logs_task")
    scheduler.add_job(
        sync_logs_task,
        "interval",
        hours=1,
        id="sync_remote_logs",
        name="Sync remote cryogenic logs",
        replace_existing=True,
        misfire_grace_time=600,  # Allow up to 10 minutes grace for missed jobs
    )
    logger.debug("Job added to scheduler")
    scheduler.start()
    logger.debug("Scheduler started successfully")
    logger.info(
        "Log synchronization scheduler started (interval: 1 hour, timezone: America/Toronto)"
    )

    yield

    # Shutdown
    logger.debug("Application shutdown: stopping scheduler")
    scheduler.shutdown()
    logger.debug("Scheduler stopped")
    logger.info("Log synchronization scheduler stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        lifespan=lifespan,
    )

    # Add slowapi rate limiter
    app.state.limiter = limiter

    # Add middleware to log HTTP requests
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests with method, path, and response status."""
        start_time = time.time()
        logger.debug(f"→ {request.method} {request.url.path}")

        response = await call_next(request)

        process_time = time.time() - start_time
        logger.info(
            f"← {request.method} {request.url.path} {response.status_code} ({process_time:.3f}s)"
        )
        return response

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
