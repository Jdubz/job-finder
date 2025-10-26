"""Logging configuration with Google Cloud Logging JSON output."""

import json
import logging
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


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

    Args:
        company_name: The full company name to format.
        max_length: Maximum length for display version. If None, uses config value.

    Returns:
        Tuple of (full_name, display_name)
    """
    if not company_name:
        return "", ""

    full_name = company_name.strip()

    if max_length is None:
        config = _load_logging_config()
        max_length = config["console"]["max_company_name_length"]

    if max_length <= 0 or len(full_name) <= max_length:
        return full_name, full_name

    if max_length <= 3:
        display_name = full_name[:max_length]
    else:
        display_name = full_name[: max_length - 3] + "..."

    return full_name, display_name


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs in JSON format matching the StructuredLogEntry schema
    from @jsdubzw/job-finder-shared-types.
    """

    def __init__(self, environment: str = "development"):
        """
        Initialize JSON formatter.

        Args:
            environment: Environment name (staging, production, development)
        """
        super().__init__()
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string conforming to StructuredLogEntry schema
        """
        # Map Python log levels to Cloud Logging severity
        severity_map = {
            logging.DEBUG: "DEBUG",
            logging.INFO: "INFO",
            logging.WARNING: "WARNING",
            logging.ERROR: "ERROR",
            logging.CRITICAL: "ERROR",
        }
        severity = severity_map.get(record.levelno, "INFO")

        # Build structured log entry
        log_entry: Dict[str, Any] = {
            "severity": severity,
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "environment": self.environment,
            "service": "worker",
        }

        # Check if record has structured fields (from StructuredLogger)
        if hasattr(record, "structured_fields"):
            # Merge structured fields from StructuredLogger
            log_entry.update(record.structured_fields)
        else:
            # Fallback to simple logging
            log_entry.update(
                {
                    "category": "system",
                    "action": "log",
                    "message": record.getMessage(),
                }
            )

        # Add error information if present
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            log_entry["error"] = {
                "type": exc_type.__name__ if exc_type else "Exception",
                "message": str(exc_value),
                "stack": self.formatException(record.exc_info) if exc_tb else None,
            }

        return json.dumps(log_entry)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_cloud_logging: bool = False,
) -> None:
    """
    Configure logging with JSON output and optional Google Cloud Logging integration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to log file. If None, uses centralized /logs/worker.log.
        enable_cloud_logging: Enable Google Cloud Logging integration.

    Environment Variables:
        ENABLE_CLOUD_LOGGING: Set to 'true' to enable Cloud Logging.
        LOG_LEVEL: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        LOG_FILE: Override log file path.
        ENVIRONMENT: Environment name (staging, production, development).
        GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON (required for Cloud Logging).
    """
    # Check environment variables
    if os.getenv("ENABLE_CLOUD_LOGGING", "").lower() == "true":
        enable_cloud_logging = True

    log_level = os.getenv("LOG_LEVEL", log_level).upper()
    # Default to centralized log directory
    if log_file is None and "LOG_FILE" not in os.environ:
        # Calculate path to service logs directory
        # worker is at: job-finder-app-manager/job-finder-worker/src/job_finder/
        # logs are at: job-finder-app-manager/job-finder-worker/logs/
        centralized_logs = Path(__file__).parent.parent.parent.parent / "logs" / "worker.log"
        log_file = str(centralized_logs)
    else:
        log_file = os.getenv("LOG_FILE", log_file)
    environment = os.getenv("ENVIRONMENT", "development")

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create JSON formatter
    json_formatter = JSONFormatter(environment=environment)

    # Configure handlers
    handlers = []

    # Console handler (JSON output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    console_handler.setLevel(getattr(logging, log_level))
    handlers.append(console_handler)

    # File handler (JSON output)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(getattr(logging, log_level))
    handlers.append(file_handler)

    # Set up Cloud Logging if enabled
    if enable_cloud_logging:
        try:
            import google.cloud.logging
            from google.cloud.logging.handlers import CloudLoggingHandler

            # Initialize Cloud Logging client
            client = google.cloud.logging.Client()

            # Create Cloud Logging handler with environment labels
            labels = {
                "environment": environment,
                "service": "job-finder",
                "version": "1.0.0",
            }

            cloud_handler = CloudLoggingHandler(
                client,
                name="job-finder",
                labels=labels,
            )
            cloud_handler.setLevel(getattr(logging, log_level))
            # Cloud handler will receive structured fields automatically
            cloud_handler.setFormatter(json_formatter)
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

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        handlers=handlers,
        force=True,
    )

    # Log startup info
    logger = logging.getLogger(__name__)
    structured = StructuredLogger(logger)
    structured.worker_status(
        "logging_configured",
        details={
            "environment": environment,
            "level": log_level,
            "file": log_file,
            "cloud_logging": enable_cloud_logging,
        },
    )


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
    Helper class for structured logging with JSON output.

    Conforms to StructuredLogEntry schema from @jsdubzw/job-finder-shared-types.
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize structured logger.

        Args:
            logger: Base logger instance
        """
        self.logger = logger
        self.environment = os.getenv("ENVIRONMENT", "development")

    def _log(self, level: str, structured_fields: Dict[str, Any]) -> None:
        """
        Log with structured fields.

        Args:
            level: Log level (debug, info, warning, error)
            structured_fields: Structured log entry fields
        """
        # Create log record
        log_method = getattr(self.logger, level.lower())

        # Get message for log record (used by some handlers)
        message = structured_fields.get("message", "")

        # Store structured fields in extra data
        extra = {"structured_fields": structured_fields}

        # Log with structured fields
        log_method(message, extra=extra)

    def queue_item_processing(
        self, item_id: str, item_type: str, action: str, details: Optional[Dict] = None
    ) -> None:
        """
        Log queue item processing.

        Args:
            item_id: Queue item ID
            item_type: Type of queue item (job, company, scrape, source_discovery)
            action: Action being performed (processing, completed, failed)
            details: Optional additional details
        """
        structured_fields = {
            "category": "queue",
            "action": action,
            "message": f"Queue item {action}",
            "queueItemId": item_id,
            "queueItemType": item_type.lower(),
            "details": details or {},
        }
        self._log("info", structured_fields)

    def pipeline_stage(
        self, item_id: str, stage: str, status: str, details: Optional[Dict] = None
    ) -> None:
        """
        Log pipeline stage transitions.

        Args:
            item_id: Queue item ID
            stage: Pipeline stage (scrape, filter, analyze, save)
            status: Stage status (started, completed, failed, skipped)
            details: Optional additional details
        """
        structured_fields = {
            "category": "pipeline",
            "action": status,
            "message": f"Pipeline {stage} {status}",
            "queueItemId": item_id,
            "pipelineStage": stage.lower(),
            "details": details or {},
        }

        # Determine log level based on status
        level = "info"
        if status.lower() in ["failed", "error"]:
            level = "error"
        elif status.lower() == "skipped":
            level = "warning"

        self._log(level, structured_fields)

    def scrape_activity(self, source: str, action: str, details: Optional[Dict] = None) -> None:
        """
        Log scraping activity.

        Args:
            source: Source being scraped
            action: Action being performed
            details: Optional additional details
        """
        structured_fields = {
            "category": "scrape",
            "action": action,
            "message": f"Scraping {source}",
            "details": {"source": source, **(details or {})},
        }
        self._log("info", structured_fields)

    def company_activity(
        self, company_name: str, action: str, details: Optional[Dict] = None, truncate: bool = True
    ) -> None:
        """
        Log company-related activity.

        Args:
            company_name: Company name
            action: Action being performed
            details: Optional additional details
            truncate: Whether to truncate for display (unused in JSON mode)
        """
        full_name, display_name = format_company_name(company_name)

        structured_fields = {
            "category": "database",
            "action": action.lower(),
            "message": f"Company {action.lower()}: {display_name}",
            "details": {
                "company_name": full_name,
                "company_name_display": display_name,
                **(details or {}),
            },
        }
        self._log("info", structured_fields)

    def ai_activity(self, operation: str, status: str, details: Optional[Dict] = None) -> None:
        """
        Log AI operations.

        Args:
            operation: AI operation (match, analyze, extract)
            status: Operation status
            details: Optional additional details (model, tokens, cost)
        """
        structured_fields = {
            "category": "ai",
            "action": operation.lower(),
            "message": f"AI {operation} {status}",
            "details": details or {},
        }
        self._log("info", structured_fields)

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
        structured_fields = {
            "category": "database",
            "action": operation.lower(),
            "message": f"Database {operation} on {collection}: {status}",
            "details": {"collection": collection, "status": status, **(details or {})},
        }
        self._log("info", structured_fields)

    def worker_status(self, status: str, details: Optional[Dict] = None) -> None:
        """
        Log worker status changes.

        Args:
            status: Worker status (started, stopping, idle, processing)
            details: Optional additional details
        """
        structured_fields = {
            "category": "worker",
            "action": status.lower(),
            "message": f"Worker {status}",
            "details": details or {},
        }
        self._log("info", structured_fields)


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
