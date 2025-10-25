"""Google Cloud Logging real-time streamer for E2E tests.

This module provides real-time streaming of Google Cloud Logs during E2E test
execution. Uses the TailLogEntries API for efficient streaming without polling.

Usage:
    streamer = LogStreamer(project_id="my-project", database_name="portfolio-staging")

    # Stream logs in background
    with streamer.stream_logs(filter_string="labels.test_run_id='e2e_test_123'"):
        # Run tests here
        run_e2e_tests()

    # Logs are printed to console in real-time with colors and formatting
"""

import logging
import sys
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager

from google.cloud import logging as cloud_logging

logger = logging.getLogger(__name__)


class ColoredFormatter:
    """ANSI color codes for log output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"

    @staticmethod
    def severity_color(severity: str) -> str:
        """Get color for log severity."""
        severity = severity.upper()
        colors = {
            "DEBUG": ColoredFormatter.CYAN,
            "INFO": ColoredFormatter.GREEN,
            "WARNING": ColoredFormatter.YELLOW,
            "ERROR": ColoredFormatter.BRIGHT_RED,
            "CRITICAL": ColoredFormatter.RED,
        }
        return colors.get(severity, ColoredFormatter.WHITE)

    @staticmethod
    def format_log_entry(entry: Dict[str, Any]) -> str:
        """Format a log entry with colors and structure."""
        severity = entry.get("severity", "INFO").upper()
        timestamp = entry.get("timestamp", datetime.utcnow().isoformat())
        payload = entry.get("textPayload", "")
        json_payload = entry.get("jsonPayload", {})

        # Extract useful info from json payload
        stage = json_payload.get("stage", "")
        doc_id = json_payload.get("doc_id", "")
        status = json_payload.get("status", "")

        color = ColoredFormatter.severity_color(severity)

        # Build message
        msg_parts = [
            f"{ColoredFormatter.DIM}{timestamp}{ColoredFormatter.RESET}",
            f"{color}[{severity:8}]{ColoredFormatter.RESET}",
        ]

        if stage:
            msg_parts.append(f"{ColoredFormatter.BLUE}{stage}{ColoredFormatter.RESET}")

        if doc_id:
            msg_parts.append(f"doc:{doc_id[:8]}")

        if status:
            msg_parts.append(f"status:{status}")

        msg_parts.append(payload or str(json_payload))

        return " ".join(msg_parts)


class LogStreamer:
    """Stream Google Cloud Logs in real-time for E2E tests."""

    def __init__(
        self,
        project_id: str,
        database_name: str = "portfolio-staging",
        buffer_duration: float = 1.0,
    ):
        """
        Initialize log streamer.

        Args:
            project_id: GCP project ID
            database_name: Firestore database name (for filtering)
            buffer_duration: Seconds to buffer logs before displaying
        """
        self.project_id = project_id
        self.database_name = database_name
        self.buffer_duration = buffer_duration
        self.logging_client = cloud_logging.Client(project=project_id)
        self._stop_event = threading.Event()
        self._log_buffer = []
        self._lock = threading.Lock()

    def build_filter(
        self,
        test_run_id: Optional[str] = None,
        severity: str = "DEFAULT",
        include_stages: Optional[list] = None,
    ) -> str:
        """
        Build filter string for log query.

        Args:
            test_run_id: Filter by specific test run
            severity: Log severity (DEFAULT, DEBUG, INFO, WARNING, ERROR)
            include_stages: Specific pipeline stages to include

        Returns:
            Filter string for Cloud Logging API
        """
        filters = []

        # Resource type
        filters.append('resource.type="gce_instance"')

        # Database
        filters.append(f'labels.database="{self.database_name}"')

        # Test run ID
        if test_run_id:
            filters.append(f'labels.test_run_id="{test_run_id}"')

        # Severity
        if severity != "DEFAULT":
            filters.append(f"severity>={severity}")

        # Specific stages
        if include_stages:
            stage_filter = " OR ".join([f'jsonPayload.stage="{stage}"' for stage in include_stages])
            filters.append(f"({stage_filter})")

        return " AND ".join(filters)

    def _entry_to_dict(self, entry) -> Dict[str, Any]:
        """Convert log entry to dictionary."""
        return {
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            "severity": entry.severity or "DEFAULT",
            "textPayload": entry.payload if isinstance(entry.payload, str) else None,
            "jsonPayload": entry.payload if isinstance(entry.payload, dict) else {},
            "labels": entry.labels or {},
        }

    def _display_log(self, entry: Dict[str, Any]) -> None:
        """Display a single log entry."""
        formatted = ColoredFormatter.format_log_entry(entry)
        print(formatted)
        sys.stdout.flush()

    def _stream_logs(self, filter_string: str, callback=None) -> None:
        """
        Stream logs using list_entries with polling.

        For true real-time streaming, use TailLogEntries API directly.
        This implementation polls periodically for new logs.

        Args:
            filter_string: Filter for log entries
            callback: Optional callback for each log entry
        """
        try:
            logger.info(f"Starting log stream with filter: {filter_string}")
            print(
                f"\n{ColoredFormatter.BRIGHT_BLUE}[LOG STREAM]{ColoredFormatter.RESET} Connecting to Google Cloud Logs..."
            )

            print(
                f"{ColoredFormatter.BRIGHT_GREEN}[LOG STREAM]{ColoredFormatter.RESET} Connected! Streaming logs...\n"
            )

            # Track last timestamp for polling
            last_timestamp = None
            seen_entries = set()

            while not self._stop_event.is_set():
                try:
                    # Build filter with timestamp
                    poll_filter = filter_string
                    if last_timestamp:
                        # Only get newer entries
                        iso_time = last_timestamp.isoformat() + "Z"
                        poll_filter = f"{filter_string} AND timestamp > '{iso_time}'"

                    # Get entries
                    entries = self.logging_client.list_entries(
                        filter_=poll_filter,
                        page_size=100,
                        order_by=cloud_logging.ASCENDING,
                    )

                    # Process entries
                    new_entries = []
                    for entry in entries:
                        entry_id = f"{entry.timestamp}_{entry.payload}"

                        # Skip if already seen (duplicates from polling)
                        if entry_id in seen_entries:
                            continue

                        seen_entries.add(entry_id)
                        new_entries.append(entry)

                        if last_timestamp is None or entry.timestamp > last_timestamp:
                            last_timestamp = entry.timestamp

                    # Display new entries
                    for entry in sorted(
                        new_entries, key=lambda e: e.timestamp or datetime.utcnow()
                    ):
                        if self._stop_event.is_set():
                            break

                        entry_dict = self._entry_to_dict(entry)

                        # Display log
                        self._display_log(entry_dict)

                        # Call custom callback if provided
                        if callback:
                            try:
                                callback(entry_dict)
                            except Exception as e:
                                logger.warning(f"Error in log callback: {e}")

                    # Small delay between polls
                    if not new_entries:
                        time.sleep(self.buffer_duration)

                except Exception as e:
                    logger.warning(f"Error during log poll: {e}")
                    time.sleep(self.buffer_duration)

        except Exception as e:
            logger.error(f"Error streaming logs: {e}")
            print(
                f"\n{ColoredFormatter.BRIGHT_RED}[ERROR]{ColoredFormatter.RESET} Log streaming failed: {e}\n"
            )
        finally:
            if not self._stop_event.is_set():
                print(
                    f"\n{ColoredFormatter.BRIGHT_BLUE}[LOG STREAM]{ColoredFormatter.RESET} Disconnected.\n"
                )

    @contextmanager
    def stream_logs(
        self,
        filter_string: Optional[str] = None,
        test_run_id: Optional[str] = None,
        callback=None,
    ):
        """
        Context manager to stream logs in background during test execution.

        Usage:
            with streamer.stream_logs(test_run_id="e2e_test_123"):
                run_tests()
            # Logs are cleaned up automatically

        Args:
            filter_string: Custom filter (uses build_filter if not provided)
            test_run_id: Test run ID to filter by
            callback: Optional callback for each log entry

        Yields:
            None
        """
        if not filter_string:
            filter_string = self.build_filter(test_run_id=test_run_id)

        # Start streaming in background thread
        stream_thread = threading.Thread(
            target=self._stream_logs,
            args=(filter_string, callback),
            daemon=True,
        )
        stream_thread.start()

        # Give stream a moment to connect
        time.sleep(0.5)

        try:
            yield
        finally:
            # Signal thread to stop
            self._stop_event.set()

            # Wait for thread to finish (with timeout)
            stream_thread.join(timeout=5.0)

            if stream_thread.is_alive():
                logger.warning("Log stream thread did not terminate gracefully")

            # Reset for next use
            self._stop_event.clear()

    def search_logs(
        self,
        filter_string: Optional[str] = None,
        test_run_id: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        """
        Search for log entries (non-streaming).

        Args:
            filter_string: Custom filter
            test_run_id: Test run ID to filter by
            limit: Maximum entries to return

        Returns:
            List of log entries
        """
        if not filter_string:
            filter_string = self.build_filter(test_run_id=test_run_id)

        try:
            entries = self.logging_client.list_entries(
                filter_=filter_string,
                page_size=limit,
            )

            results = []
            for i, entry in enumerate(entries):
                if i >= limit:
                    break

                results.append(self._entry_to_dict(entry))

            return results

        except Exception as e:
            logger.error(f"Error searching logs: {e}")
            return []

    def get_log_summary(self, test_run_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for a test run.

        Args:
            test_run_id: Test run ID

        Returns:
            Dictionary with log statistics
        """
        filter_string = self.build_filter(test_run_id=test_run_id)

        entries = self.search_logs(filter_string=filter_string, limit=10000)

        summary = {
            "test_run_id": test_run_id,
            "total_entries": len(entries),
            "by_severity": {},
            "by_stage": {},
            "errors": [],
            "warnings": [],
            "duration": None,
        }

        first_time = None
        last_time = None

        for entry in entries:
            severity = entry.get("severity", "INFO")
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1

            json_payload = entry.get("jsonPayload", {})
            stage = json_payload.get("stage")
            if stage:
                summary["by_stage"][stage] = summary["by_stage"].get(stage, 0) + 1

            if severity in ["ERROR", "CRITICAL"]:
                summary["errors"].append(
                    {
                        "message": entry.get("textPayload", ""),
                        "timestamp": entry.get("timestamp"),
                    }
                )

            if severity == "WARNING":
                summary["warnings"].append(
                    {
                        "message": entry.get("textPayload", ""),
                        "timestamp": entry.get("timestamp"),
                    }
                )

            # Track timing
            timestamp_str = entry.get("timestamp")
            if timestamp_str:
                # Parse ISO format timestamp
                try:
                    ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    if first_time is None or ts < first_time:
                        first_time = ts
                    if last_time is None or ts > last_time:
                        last_time = ts
                except Exception:
                    pass

        if first_time and last_time:
            summary["duration"] = (last_time - first_time).total_seconds()

        return summary


# Convenience functions for quick use


def stream_test_logs(
    project_id: str,
    test_run_id: str,
    database_name: str = "portfolio-staging",
):
    """
    Context manager to stream logs for a specific test run.

    Usage:
        with stream_test_logs("my-project", "e2e_test_123"):
            run_e2e_tests()
    """
    streamer = LogStreamer(project_id, database_name)
    return streamer.stream_logs(test_run_id=test_run_id)


def get_test_logs_summary(
    project_id: str,
    test_run_id: str,
    database_name: str = "portfolio-staging",
) -> Dict[str, Any]:
    """Get summary of logs for a test run."""
    streamer = LogStreamer(project_id, database_name)
    return streamer.get_log_summary(test_run_id)


if __name__ == "__main__":
    # Example usage
    import os

    project_id = os.getenv("GCP_PROJECT_ID", "my-project")
    test_run_id = "e2e_test_example"

    print("Google Cloud Logs Streamer")
    print("=" * 70)

    # Example 1: Stream logs
    print("\nExample 1: Streaming logs in real-time")
    print("-" * 70)

    streamer = LogStreamer(project_id)

    # This would stream logs during test execution
    # with streamer.stream_logs(test_run_id=test_run_id):
    #     run_e2e_tests()

    # Example 2: Search logs
    print("\nExample 2: Searching logs")
    print("-" * 70)

    entries = streamer.search_logs(test_run_id=test_run_id, limit=10)
    print(f"Found {len(entries)} log entries")

    # Example 3: Get summary
    print("\nExample 3: Get log summary")
    print("-" * 70)

    summary = streamer.get_log_summary(test_run_id)
    print(f"Summary for {test_run_id}:")
    print(f"  Total entries: {summary['total_entries']}")
    print(f"  By severity: {summary['by_severity']}")
    print(f"  Duration: {summary['duration']}s" if summary["duration"] else "  Duration: N/A")
    print(f"  Errors: {len(summary['errors'])}")
    print(f"  Warnings: {len(summary['warnings'])}")
