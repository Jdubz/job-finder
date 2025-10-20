"""Logging configuration with optional Google Cloud Logging integration."""

import logging
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Optional, Tuple


# Global configuration cache
_logging_config: Optional[Dict] = None


def _load_logging_config() -> Dict:
    """
    Load logging configuration from config/logging.yaml.

    Returns:
        Dict with logging configuration, or default config if file not found.
    """
    global _logging_config

    if _logging_config is not None:
        return _logging_config

    # Try to load from config file
    config_path = Path(__file__).parent.parent.parent / "config" / "logging.yaml"

    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                _logging_config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"⚠️  Failed to load logging config from {config_path}: {e}", file=sys.stderr)
            _logging_config = {}
    else:
        _logging_config = {}

    # Apply defaults if keys are missing
    if "console" not in _logging_config:
        _logging_config["console"] = {}
    if "structured" not in _logging_config:
        _logging_config["structured"] = {}

    _logging_config["console"].setdefault("max_company_name_length", 80)
    _logging_config["console"].setdefault("max_job_title_length", 60)
    _logging_config["console"].setdefault("max_url_length", 50)
    _logging_config["structured"].setdefault("include_display_fields", True)
    _logging_config["structured"].setdefault("preserve_full_values", True)

    return _logging_config


def format_company_name(company_name: str, max_length: Optional[int] = None) -> Tuple[str, str]:
    """
    Format a company name for logging with both full and display versions.

    This function ensures that:
    1. Full company names are always preserved for structured logging
    2. Display-friendly truncated versions are provided for console output
    3. Unicode characters are handled safely
    4. Truncation uses ellipsis (...) for readability

    Args:
        company_name: The full company name to format.
        max_length: Maximum length for display version. If None, uses config value.

    Returns:
        Tuple of (full_name, display_name) where:
        - full_name: Complete untruncated company name
        - display_name: Truncated version with ellipsis if needed

    Example:
        >>> format_company_name("Very Long Company Name That Exceeds Limit")
        ('Very Long Company Name That Exceeds Limit', 'Very Long Company Name That Exceed...')
    """
    if not company_name:
        return "", ""

    # Always preserve full name
    full_name = company_name.strip()

    # Get max length from config if not provided
    if max_length is None:
        config = _load_logging_config()
        max_length = config["console"]["max_company_name_length"]

    # If max_length is 0 or negative, no truncation
    if max_length <= 0:
        return full_name, full_name

    # If name is short enough, return as-is
    if len(full_name) <= max_length:
        return full_name, full_name

    # Truncate with ellipsis
    # Reserve 3 characters for "..."
    if max_length <= 3:
        display_name = full_name[:max_length]
    else:
        display_name = full_name[: max_length - 3] + "..."

    return full_name, display_name


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
        ENVIRONMENT: Environment name (staging, production, development) - added to Cloud Logging labels.
        GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON (required for Cloud Logging).
    """
    # Check environment variables
    if os.getenv("ENABLE_CLOUD_LOGGING", "").lower() == "true":
        enable_cloud_logging = True

    log_level = os.getenv("LOG_LEVEL", log_level).upper()
    log_file = os.getenv("LOG_FILE", log_file or "logs/job_finder.log")
    environment = os.getenv("ENVIRONMENT", "development")

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

            # Create Cloud Logging handler with environment labels
            # This ensures all logs have environment context for filtering
            labels = {
                "environment": environment,
                "service": "job-finder",
                "version": "1.0.0",  # TODO: Get from package version
            }

            cloud_handler = CloudLoggingHandler(
                client,
                name="job-finder",
                labels=labels,
            )
            # Set handler level to match root logger level (not just ERROR)
            cloud_handler.setLevel(getattr(logging, log_level))
            handlers.append(cloud_handler)

            print(f"✅ Google Cloud Logging enabled")
            print(f"   Project: {client.project}")
            print(f"   Log name: job-finder")
            print(f"   Environment: {environment}")
            print(f"   Log level: {log_level}")
            print(f"   Labels: {labels}")

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

    # Improved log format with environment prefix for better readability
    log_format = f"[{environment.upper()}] %(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=handlers,
        force=True,  # Override any existing configuration
    )

    # Log startup info
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: environment={environment}, level={log_level}, file={log_file}"
    )
    if enable_cloud_logging:
        logger.info(f"Google Cloud Logging enabled with labels: {labels}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)


class StructuredLogger:
    """
    Helper class for structured logging with consistent formatting.

    Provides methods for logging common operations with context.
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize structured logger.

        Args:
            logger: Base logger instance
        """
        self.logger = logger
        self.environment = os.getenv("ENVIRONMENT", "development")

    def queue_item_processing(
        self, item_id: str, item_type: str, action: str, details: Optional[Dict] = None
    ) -> None:
        """
        Log queue item processing with structured context.

        Args:
            item_id: Queue item ID
            item_type: Type of queue item (job, company, scrape, etc.)
            action: Action being performed (processing, completed, failed, etc.)
            details: Optional additional details
        """
        message = f"[QUEUE:{item_type.upper()}] {action} - ID:{item_id}"
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            message += f" | {detail_str}"
        self.logger.info(message)

    def pipeline_stage(
        self, item_id: str, stage: str, status: str, details: Optional[Dict] = None
    ) -> None:
        """
        Log pipeline stage transitions.

        Args:
            item_id: Queue item ID
            stage: Pipeline stage (SCRAPE, FILTER, ANALYZE, SAVE)
            status: Stage status (started, completed, failed, skipped)
            details: Optional additional details
        """
        message = f"[PIPELINE:{stage}] {status.upper()} - ID:{item_id}"
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            message += f" | {detail_str}"

        if status.lower() in ["failed", "error"]:
            self.logger.error(message)
        elif status.lower() == "skipped":
            self.logger.warning(message)
        else:
            self.logger.info(message)

    def scrape_activity(self, source: str, action: str, details: Optional[Dict] = None) -> None:
        """
        Log scraping activity.

        Args:
            source: Source being scraped (company name, URL, etc.)
            action: Action being performed
            details: Optional additional details
        """
        message = f"[SCRAPE] {action} - Source:{source}"
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            message += f" | {detail_str}"
        self.logger.info(message)

    def company_activity(
        self, company_name: str, action: str, details: Optional[Dict] = None, truncate: bool = True
    ) -> None:
        """
        Log company-related activity with smart truncation.

        This method ensures full company names are preserved in structured logs
        while providing readable truncated versions for console output.

        Args:
            company_name: Full company name
            action: Action being performed (e.g., "FETCH", "EXTRACT", "ANALYZE")
            details: Optional additional details
            truncate: Whether to use display truncation (default: True)
        """
        full_name, display_name = format_company_name(company_name)

        # Use display name for console readability
        name_to_log = display_name if truncate else full_name

        message = f"[COMPANY] {action} - {name_to_log}"
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            message += f" | {detail_str}"

        # Note: The actual full name is still available in structured logs
        # via the logging context if needed
        self.logger.info(message)

    def ai_activity(self, operation: str, status: str, details: Optional[Dict] = None) -> None:
        """
        Log AI operations.

        Args:
            operation: AI operation (match, analyze, extract, etc.)
            status: Operation status
            details: Optional additional details (model, tokens, cost, etc.)
        """
        message = f"[AI:{operation.upper()}] {status}"
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            message += f" | {detail_str}"
        self.logger.info(message)

    def database_activity(
        self, operation: str, collection: str, status: str, details: Optional[Dict] = None
    ) -> None:
        """
        Log database operations.

        Args:
            operation: Database operation (create, update, delete, query)
            collection: Firestore collection name
            status: Operation status
            details: Optional additional details
        """
        message = f"[DB:{operation.upper()}] {collection} - {status}"
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            message += f" | {detail_str}"
        self.logger.info(message)

    def worker_status(self, status: str, details: Optional[Dict] = None) -> None:
        """
        Log worker status changes.

        Args:
            status: Worker status (started, stopping, idle, processing)
            details: Optional additional details
        """
        message = f"[WORKER] {status.upper()}"
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            message += f" | {detail_str}"
        self.logger.info(message)


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        StructuredLogger instance.
    """
    base_logger = logging.getLogger(name)
    return StructuredLogger(base_logger)
