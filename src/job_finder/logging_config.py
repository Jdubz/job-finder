"""Logging configuration with optional Google Cloud Logging integration."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_cloud_logging: bool = False,
) -> None:
    """
    Configure logging with optional Google Cloud Logging integration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to log file. If None, uses logs/job_finder.log.
        enable_cloud_logging: Enable Google Cloud Logging integration.

    Environment Variables:
        ENABLE_CLOUD_LOGGING: Set to 'true' to enable Cloud Logging.
        LOG_LEVEL: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        LOG_FILE: Override log file path.
        GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON (required for Cloud Logging).
    """
    # Check environment variables
    if os.getenv("ENABLE_CLOUD_LOGGING", "").lower() == "true":
        enable_cloud_logging = True

    log_level = os.getenv("LOG_LEVEL", log_level).upper()
    log_file = os.getenv("LOG_FILE", log_file or "logs/job_finder.log")

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure basic logging
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file),
    ]

    # Set up Cloud Logging if enabled
    if enable_cloud_logging:
        try:
            import google.cloud.logging
            from google.cloud.logging.handlers import CloudLoggingHandler

            # Initialize Cloud Logging client
            client = google.cloud.logging.Client()

            # Create Cloud Logging handler
            cloud_handler = CloudLoggingHandler(client, name="job-finder")
            # Set handler level to match root logger level (not just ERROR)
            cloud_handler.setLevel(getattr(logging, log_level))
            handlers.append(cloud_handler)

            print(f"✅ Google Cloud Logging enabled - logs will appear in Google Cloud Console")
            print(f"   Project: {client.project}")
            print(f"   Log name: job-finder")
            print(f"   Log level: {log_level}")

        except ImportError:
            print(
                "⚠️  google-cloud-logging not installed. Install with: pip install google-cloud-logging",
                file=sys.stderr,
            )
            print("   Falling back to file and console logging only.", file=sys.stderr)

        except Exception as e:
            print(
                f"⚠️  Failed to initialize Google Cloud Logging: {e}",
                file=sys.stderr,
            )
            print("   Falling back to file and console logging only.", file=sys.stderr)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,  # Override any existing configuration
    )

    # Log startup info
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={log_level}, file={log_file}")
    if enable_cloud_logging:
        logger.info("Google Cloud Logging integration enabled")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)
