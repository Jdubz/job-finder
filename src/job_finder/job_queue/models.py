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
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class QueueItemType(str, Enum):
    """
    Type of queue item.

    TypeScript equivalent: QueueItemType in queue.types.ts
    Values must match exactly: "job" | "company" | "scrape" | "source_discovery" | "scrape_source"
    """

    JOB = "job"
    COMPANY = "company"
    SCRAPE = "scrape"
    SOURCE_DISCOVERY = "source_discovery"
    SCRAPE_SOURCE = "scrape_source"  # NEW: For automated source scraping


class JobSubTask(str, Enum):
    """
    Granular sub-tasks for job processing pipeline.

    When a JOB queue item has a sub_task, it represents one step in the
    multi-stage processing pipeline. Items without sub_task (legacy) are
    processed monolithically through all stages.

    Pipeline flow:
    1. JOB_SCRAPE: Fetch HTML and extract basic job data (Claude Haiku)
    2. JOB_FILTER: Apply strike-based filtering (no AI)
    3. JOB_ANALYZE: AI matching and resume intake generation (Claude Sonnet)
    4. JOB_SAVE: Save results to job-matches (no AI)

    TypeScript equivalent: JobSubTask in queue.types.ts
    """

    SCRAPE = "scrape"
    FILTER = "filter"
    ANALYZE = "analyze"
    SAVE = "save"


class CompanySubTask(str, Enum):
    """
    Granular sub-tasks for company processing pipeline.

    When a COMPANY queue item has a company_sub_task, it represents one step in the
    multi-stage processing pipeline. Items without company_sub_task (legacy) are
    processed monolithically through all stages.

    Pipeline flow:
    1. FETCH: Fetch website HTML content (cheap AI if needed)
    2. EXTRACT: Extract company info using AI (expensive AI)
    3. ANALYZE: Tech stack detection, job board discovery, priority scoring (rule-based)
    4. SAVE: Save to Firestore, spawn source_discovery if job board found (no AI)

    TypeScript equivalent: CompanySubTask in queue.types.ts
    """

    FETCH = "fetch"
    EXTRACT = "extract"
    ANALYZE = "analyze"
    SAVE = "save"


class CompanyStatus(str, Enum):
    """
    Status for company records in Firestore.

    Tracks the analysis state of a company.

    TypeScript equivalent: CompanyStatus in queue.types.ts
    """

    PENDING = "pending"  # Initial state, not yet analyzed
    ANALYZING = "analyzing"  # Currently being processed through pipeline
    ACTIVE = "active"  # Analysis complete, ready for use
    FAILED = "failed"  # Analysis failed after retries


class SourceStatus(str, Enum):
    """
    Status for job source records in Firestore.

    Tracks the validation and operational state of a scraping source.

    TypeScript equivalent: SourceStatus in queue.types.ts
    """

    PENDING_VALIDATION = "pending_validation"  # Discovered but needs manual validation
    ACTIVE = "active"  # Validated and enabled for scraping
    DISABLED = "disabled"  # Manually or automatically disabled
    FAILED = "failed"  # Permanently failed validation or operation


class SourceTier(str, Enum):
    """
    Priority tier for company/source scraping.

    Based on scoring algorithm:
    - Portland office: +50 points
    - Tech stack alignment: up to +100 points
    - Remote-first culture: +15 points
    - AI/ML focus: +10 points

    Tiers:
    - S: 150+ points (top priority)
    - A: 100-149 points (high priority)
    - B: 70-99 points (medium priority)
    - C: 50-69 points (low priority)
    - D: 0-49 points (minimal priority)

    TypeScript equivalent: SourceTier in queue.types.ts
    """

    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"


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


class ScrapeConfig(BaseModel):
    """
    Configuration for a scrape request.

    Used when QueueItemType is SCRAPE to specify custom scraping parameters.

    Behavior:
    - source_ids=None → scrape all available sources (with rotation)
    - source_ids=[...] → scrape only specific sources
    - target_matches=None → no early exit, scrape all allowed sources
    - target_matches=N → stop after finding N potential matches
    - max_sources=None → unlimited sources (until target_matches or all sources done)
    - max_sources=N → stop after scraping N sources
    """

    target_matches: Optional[int] = Field(
        default=5,
        description="Stop after finding this many potential matches (None = no limit)",
    )
    max_sources: Optional[int] = Field(
        default=20,
        description="Maximum number of sources to scrape (None = unlimited)",
    )
    source_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific source IDs to scrape (None = all sources with rotation)",
    )
    min_match_score: Optional[int] = Field(
        default=None, description="Override minimum match score threshold"
    )

    model_config = ConfigDict(use_enum_values=True)


class SourceTypeHint(str, Enum):
    """
    Source type hint for discovery.

    TypeScript equivalent: SourceTypeHint in queue.types.ts
    """

    AUTO = "auto"
    GREENHOUSE = "greenhouse"
    WORKDAY = "workday"
    RSS = "rss"
    GENERIC = "generic"


class SourceDiscoveryConfig(BaseModel):
    """
    Configuration for source discovery requests.

    Used when QueueItemType is SOURCE_DISCOVERY to discover and configure a new job source.

    Flow:
    1. job-finder-FE submits URL for discovery
    2. Job-finder detects source type (greenhouse, workday, rss, generic)
    3. For known types: validate and create config
    4. For generic: use AI selector discovery
    5. Test scrape to validate
    6. Create job-source document if successful

    TypeScript equivalent: SourceDiscoveryConfig in queue.types.ts
    """

    url: str = Field(description="URL to analyze and configure")
    type_hint: Optional[SourceTypeHint] = Field(
        default=SourceTypeHint.AUTO, description="Optional hint about source type"
    )
    company_id: Optional[str] = Field(default=None, description="Optional company reference")
    company_name: Optional[str] = Field(default=None, description="Optional company name")
    auto_enable: bool = Field(
        default=True, description="Auto-enable if discovery succeeds (default: true)"
    )
    validation_required: bool = Field(
        default=False, description="Require manual validation before enabling (default: false)"
    )

    model_config = ConfigDict(use_enum_values=True)


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
    url: str = Field(
        default="", description="URL to scrape (job posting or company page, empty for SCRAPE type)"
    )
    company_name: str = Field(default="", description="Company name (empty for SCRAPE type)")
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

    # Scrape configuration (only used when type is SCRAPE)
    scrape_config: Optional[ScrapeConfig] = Field(
        default=None, description="Configuration for scrape requests"
    )

    # Source discovery configuration (only used when type is SOURCE_DISCOVERY)
    source_discovery_config: Optional[SourceDiscoveryConfig] = Field(
        default=None, description="Configuration for source discovery"
    )

    # Scrape source fields (only used when type is SCRAPE_SOURCE)
    source_id: Optional[str] = Field(
        default=None,
        description="Reference to job-sources Firestore document (for SCRAPE_SOURCE type)",
    )
    source_type: Optional[str] = Field(
        default=None, description="Type of source: greenhouse, rss, workday, lever, api, scraper"
    )
    source_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Source-specific configuration (selectors, API keys, etc.)"
    )
    source_tier: Optional[SourceTier] = Field(
        default=None, description="Priority tier (S/A/B/C/D) for scheduling optimization"
    )

    # Granular pipeline fields (only used when type is JOB with sub_task)
    sub_task: Optional[JobSubTask] = Field(
        default=None,
        description="Granular pipeline step (scrape/filter/analyze/save). None = legacy monolithic processing",
    )
    pipeline_state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="State passed between pipeline steps (scraped data, filter results, etc.)",
    )
    parent_item_id: Optional[str] = Field(
        default=None, description="Document ID of parent item that spawned this sub-task"
    )

    # Company granular pipeline fields (only used when type is COMPANY with company_sub_task)
    company_sub_task: Optional[CompanySubTask] = Field(
        default=None,
        description="Company pipeline step (fetch/extract/analyze/save). None = legacy monolithic processing",
    )

    # Loop prevention fields (auto-generated if not provided)
    tracking_id: str = Field(
        default_factory=lambda: str(__import__("uuid").uuid4()),
        description="UUID that tracks entire job lineage. Generated at root, inherited by all spawned children.",
    )
    ancestry_chain: List[str] = Field(
        default_factory=list,
        description="Chain of parent item IDs from root to current. Used to detect circular dependencies.",
    )
    spawn_depth: int = Field(
        default=0,
        description="Recursion depth in spawn chain. Root items = 0, increments by 1 with each spawn.",
    )
    max_spawn_depth: int = Field(
        default=10,
        description="Maximum allowed spawn depth before blocking to prevent infinite loops.",
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
