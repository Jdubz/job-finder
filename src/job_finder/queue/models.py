"""Pydantic models for queue items."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class QueueItemType(str, Enum):
    """Type of queue item."""

    JOB = "job"
    COMPANY = "company"


class QueueStatus(str, Enum):
    """Status of queue item processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    SKIPPED = "skipped"
    FAILED = "failed"
    SUCCESS = "success"


class JobQueueItem(BaseModel):
    """
    Queue item representing a job or company to be processed.

    This model represents items in the job-queue Firestore collection.
    Items are processed in FIFO order (oldest created_at first).
    """

    # Identity
    id: Optional[str] = None  # Set by Firestore
    type: QueueItemType = Field(description="Type of item (job or company)")

    # Status tracking
    status: QueueStatus = Field(
        default=QueueStatus.PENDING, description="Current processing status"
    )
    result_message: Optional[str] = Field(
        default=None, description="Why skipped/failed, or success details"
    )

    # Input data
    url: str = Field(description="URL to scrape (job posting or company page)")
    company_name: Optional[str] = Field(default=None, description="Company name if known")
    company_id: Optional[str] = Field(default=None, description="Firestore company document ID")
    source: str = Field(
        default="scraper",
        description="Source of submission: scraper, user_submission, webhook, email",
    )
    submitted_by: Optional[str] = Field(
        default=None, description="User ID if submitted by authenticated user"
    )

    # Processing data
    scraped_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Data scraped from URL (flexible structure)"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts before failure")

    # Timestamps (for FIFO ordering)
    created_at: Optional[datetime] = Field(default=None, description="When item was added to queue")
    updated_at: Optional[datetime] = Field(default=None, description="Last update to status/data")
    processed_at: Optional[datetime] = Field(default=None, description="When processing started")
    completed_at: Optional[datetime] = Field(
        default=None, description="When processing finished (success/failed/skipped)"
    )

    model_config = ConfigDict(use_enum_values=True)

    def to_firestore(self) -> Dict[str, Any]:
        """
        Convert to Firestore document format.

        Excludes None values and converts datetimes to Firestore timestamps.
        """
        data = self.model_dump(exclude_none=True, exclude={"id"})
        return data

    @classmethod
    def from_firestore(cls, doc_id: str, data: Dict[str, Any]) -> "JobQueueItem":
        """
        Create JobQueueItem from Firestore document.

        Args:
            doc_id: Firestore document ID
            data: Document data

        Returns:
            JobQueueItem instance
        """
        data["id"] = doc_id
        return cls(**data)
