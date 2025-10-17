"""
Pydantic models for queue items.

These models are derived from TypeScript definitions in @jdubz/job-finder-shared-types.
See: https://github.com/Jdubz/job-finder-shared-types/blob/main/src/queue.types.ts

IMPORTANT: TypeScript types are the source of truth. When modifying queue schema:
1. Update TypeScript first in shared-types GitHub repository
2. Create PR, merge, and publish new npm version
3. Update these Python models to match
4. Test compatibility with portfolio project
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class QueueItemType(str, Enum):
    """
    Type of queue item.

    TypeScript equivalent: QueueItemType in queue.types.ts
    Values must match exactly: "job" | "company"
    """

    JOB = "job"
    COMPANY = "company"


class QueueStatus(str, Enum):
    """
    Status of queue item processing.

    TypeScript equivalent: QueueStatus in queue.types.ts
    Lifecycle: pending → processing → success/failed/skipped/filtered

    - PENDING: In queue, waiting to be processed
    - PROCESSING: Currently being processed
    - FILTERED: Rejected by filter engine (did not pass intake filters)
    - SKIPPED: Skipped (duplicate or stop list blocked)
    - SUCCESS: Successfully processed and saved to job-matches
    - FAILED: Processing error occurred
    """

    PENDING = "pending"
    PROCESSING = "processing"
    FILTERED = "filtered"
    SKIPPED = "skipped"
    FAILED = "failed"
    SUCCESS = "success"


# QueueSource type - matches TypeScript literal type
# TypeScript: "user_submission" | "automated_scan" | "scraper" | "webhook" | "email"
QueueSource = Literal["user_submission", "automated_scan", "scraper", "webhook", "email"]


class JobQueueItem(BaseModel):
    """
    Queue item representing a job or company to be processed.

    TypeScript equivalent: QueueItem interface in queue.types.ts
    This model represents items in the job-queue Firestore collection.
    Items are processed in FIFO order (oldest created_at first).

    IMPORTANT: This model must match the TypeScript QueueItem interface exactly.
    See: https://github.com/Jdubz/job-finder-shared-types/blob/main/src/queue.types.ts
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
    error_details: Optional[str] = Field(
        default=None, description="Technical error details for debugging"
    )

    # Input data
    url: str = Field(description="URL to scrape (job posting or company page)")
    company_name: str = Field(description="Company name")
    company_id: Optional[str] = Field(default=None, description="Firestore company document ID")
    source: QueueSource = Field(
        default="scraper",
        description="Source of submission: scraper, user_submission, webhook, email",
    )
    submitted_by: Optional[str] = Field(
        default=None, description="User ID if submitted by authenticated user"
    )

    # Processing data
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts before failure")

    # Timestamps (for FIFO ordering)
    created_at: Optional[datetime] = Field(default=None, description="When item was added to queue")
    updated_at: Optional[datetime] = Field(default=None, description="Last update to status/data")
    processed_at: Optional[datetime] = Field(default=None, description="When processing started")
    completed_at: Optional[datetime] = Field(
        default=None, description="When processing finished (success/failed/skipped)"
    )

    # Optional scraped data (populated by scrapers or API submissions)
    scraped_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Pre-scraped job or company data"
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
