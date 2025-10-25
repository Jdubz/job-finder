"""
Data Quality and Completeness Monitor for E2E Tests

Monitors accuracy and completeness of company data, job source data, and job listings.
Provides metrics on data quality improvements from E2E test runs.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class DataEntityType(Enum):
    """Types of data entities to monitor."""

    COMPANY = "company"
    JOB_SOURCE = "job-source"
    JOB_MATCH = "job-match"


class CompletionLevel(Enum):
    """Data completeness levels."""

    MINIMAL = "minimal"  # Only required fields
    PARTIAL = "partial"  # Most recommended fields
    COMPLETE = "complete"  # All fields including optional


@dataclass
class FieldValidation:
    """Validation rule for a field."""

    name: str
    required: bool = False
    data_type: type = str
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_values: Optional[List[str]] = None
    validate_url: bool = False


@dataclass
class EntityMetrics:
    """Metrics for a single entity."""

    entity_id: str
    entity_type: DataEntityType
    entity_data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Quality metrics
    total_fields: int = 0
    required_fields_present: int = 0
    recommended_fields_present: int = 0
    optional_fields_present: int = 0
    validation_errors: List[str] = field(default_factory=list)
    data_issues: List[str] = field(default_factory=list)

    # Scoring
    completeness_score: float = 0.0  # 0-100
    accuracy_score: float = 0.0  # 0-100
    overall_quality_score: float = 0.0  # 0-100

    @property
    def completion_level(self) -> CompletionLevel:
        """Determine data completion level."""
        required_pct = (
            (self.required_fields_present / self.total_fields * 100) if self.total_fields > 0 else 0
        )
        recommended_pct = (
            (self.recommended_fields_present / self.total_fields * 100)
            if self.total_fields > 0
            else 0
        )

        if required_pct == 100 and recommended_pct == 100:
            return CompletionLevel.COMPLETE
        elif required_pct == 100 and recommended_pct > 50:
            return CompletionLevel.PARTIAL
        else:
            return CompletionLevel.MINIMAL

    @property
    def is_valid(self) -> bool:
        """Check if entity passed all validations."""
        return len(self.validation_errors) == 0

    @property
    def is_healthy(self) -> bool:
        """Check if entity is overall healthy."""
        return self.is_valid and len(self.data_issues) == 0 and self.overall_quality_score >= 80


@dataclass
class TestDataQualityReport:
    """Report of data quality for a test run."""

    test_run_id: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None

    # Entity counts
    companies_processed: int = 0
    sources_processed: int = 0
    jobs_processed: int = 0

    # Quality tracking
    entity_metrics: Dict[str, EntityMetrics] = field(default_factory=dict)
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    issues_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Improvement metrics
    improved_entities: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    created_entities: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def duration(self) -> float:
        """Get report duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def average_quality_score(self) -> float:
        """Get average quality score across all entities."""
        if not self.entity_metrics:
            return 0.0
        scores = [m.overall_quality_score for m in self.entity_metrics.values()]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def average_completeness_score(self) -> float:
        """Get average completeness score."""
        if not self.entity_metrics:
            return 0.0
        scores = [m.completeness_score for m in self.entity_metrics.values()]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def healthy_entities(self) -> int:
        """Count entities that are healthy."""
        return sum(1 for m in self.entity_metrics.values() if m.is_healthy)

    @property
    def total_entities(self) -> int:
        """Count total entities."""
        return len(self.entity_metrics)


class DataQualityMonitor:
    """Monitors data quality and completeness for E2E tests."""

    def __init__(self):
        """Initialize monitor."""
        self.report: Optional[TestDataQualityReport] = None
        self._current_test_run_id: Optional[str] = None

    def start_test_run(self, test_run_id: str) -> None:
        """
        Start monitoring a test run.

        Args:
            test_run_id: Unique identifier for test run
        """
        self._current_test_run_id = test_run_id
        self.report = TestDataQualityReport(test_run_id=test_run_id)
        logger.info(f"Data quality monitoring started for test run: {test_run_id}")

    def end_test_run(self) -> TestDataQualityReport:
        """
        End monitoring and return report.

        Returns:
            TestDataQualityReport with all collected metrics
        """
        if not self.report:
            raise RuntimeError("No active test run. Call start_test_run() first.")

        self.report.end_time = datetime.utcnow()
        logger.info(f"Data quality monitoring ended. Duration: {self.report.duration:.1f}s")
        return self.report

    def track_company(
        self,
        company_id: str,
        company_data: Dict[str, Any],
        is_new: bool = True,
        was_improved: bool = False,
    ) -> EntityMetrics:
        """
        Track company data quality.

        Args:
            company_id: Company document ID
            company_data: Company data dictionary
            is_new: Whether this is a newly created company
            was_improved: Whether this company data was improved

        Returns:
            EntityMetrics for the company
        """
        if not self.report:
            raise RuntimeError("No active test run. Call start_test_run() first.")

        metrics = self._validate_company(company_id, company_data)

        # Track counts
        self.report.companies_processed += 1
        if is_new:
            self.report.created_entities["company"] += 1
        if was_improved:
            self.report.improved_entities["company"] += 1

        # Store metrics
        self.report.entity_metrics[f"company:{company_id}"] = metrics

        return metrics

    def track_job_source(
        self,
        source_id: str,
        source_data: Dict[str, Any],
        is_new: bool = True,
        was_improved: bool = False,
    ) -> EntityMetrics:
        """
        Track job source data quality.

        Args:
            source_id: Job source document ID
            source_data: Job source data dictionary
            is_new: Whether this is a newly created source
            was_improved: Whether this source data was improved

        Returns:
            EntityMetrics for the source
        """
        if not self.report:
            raise RuntimeError("No active test run. Call start_test_run() first.")

        metrics = self._validate_job_source(source_id, source_data)

        # Track counts
        self.report.sources_processed += 1
        if is_new:
            self.report.created_entities["source"] += 1
        if was_improved:
            self.report.improved_entities["source"] += 1

        # Store metrics
        self.report.entity_metrics[f"source:{source_id}"] = metrics

        return metrics

    def track_job_match(
        self,
        job_id: str,
        job_data: Dict[str, Any],
        is_new: bool = True,
        was_improved: bool = False,
    ) -> EntityMetrics:
        """
        Track job match data quality.

        Args:
            job_id: Job match document ID
            job_data: Job match data dictionary
            is_new: Whether this is a newly created match
            was_improved: Whether this job data was improved

        Returns:
            EntityMetrics for the job
        """
        if not self.report:
            raise RuntimeError("No active test run. Call start_test_run() first.")

        metrics = self._validate_job_match(job_id, job_data)

        # Track counts
        self.report.jobs_processed += 1
        if is_new:
            self.report.created_entities["job"] += 1
        if was_improved:
            self.report.improved_entities["job"] += 1

        # Store metrics
        self.report.entity_metrics[f"job:{job_id}"] = metrics

        return metrics

    def log_data_issue(self, entity_id: str, issue: str) -> None:
        """
        Log a data quality issue for an entity.

        Args:
            entity_id: Entity identifier
            issue: Description of the issue
        """
        if not self.report:
            return

        # Find metric for entity
        for key, metric in self.report.entity_metrics.items():
            if entity_id in key:
                metric.data_issues.append(issue)
                issue_type = issue.split(":")[0] if ":" in issue else "other"
                self.report.issues_by_type[issue_type] += 1
                break

    def get_report(self) -> Optional[TestDataQualityReport]:
        """Get current report without ending test run."""
        return self.report

    def get_report_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the data quality report.

        Returns:
            Dictionary with report summary
        """
        if not self.report:
            return {}

        return {
            "test_run_id": self.report.test_run_id,
            "duration_seconds": self.report.duration,
            "entities_processed": {
                "companies": self.report.companies_processed,
                "sources": self.report.sources_processed,
                "jobs": self.report.jobs_processed,
                "total": self.report.total_entities,
            },
            "created_entities": dict(self.report.created_entities),
            "improved_entities": dict(self.report.improved_entities),
            "quality_scores": {
                "average": round(self.report.average_quality_score, 1),
                "average_completeness": round(self.report.average_completeness_score, 1),
                "healthy_entities": self.report.healthy_entities,
            },
            "issues": {
                "validation_errors": sum(self.report.errors_by_type.values()),
                "data_issues": sum(self.report.issues_by_type.values()),
                "by_type": {
                    "errors": dict(self.report.errors_by_type),
                    "issues": dict(self.report.issues_by_type),
                },
            },
        }

    def _validate_company(self, company_id: str, data: Dict[str, Any]) -> EntityMetrics:
        """Validate company data."""
        schema = self._get_company_schema()
        return self._validate_entity(company_id, data, schema, DataEntityType.COMPANY)

    def _validate_job_source(self, source_id: str, data: Dict[str, Any]) -> EntityMetrics:
        """Validate job source data."""
        schema = self._get_job_source_schema()
        return self._validate_entity(source_id, data, schema, DataEntityType.JOB_SOURCE)

    def _validate_job_match(self, job_id: str, data: Dict[str, Any]) -> EntityMetrics:
        """Validate job match data."""
        schema = self._get_job_match_schema()
        return self._validate_entity(job_id, data, schema, DataEntityType.JOB_MATCH)

    def _validate_entity(
        self,
        entity_id: str,
        data: Dict[str, Any],
        schema: List[FieldValidation],
        entity_type: DataEntityType,
    ) -> EntityMetrics:
        """
        Validate an entity against schema.

        Args:
            entity_id: Entity identifier
            data: Entity data
            schema: Validation schema
            entity_type: Type of entity

        Returns:
            EntityMetrics with validation results
        """
        metrics = EntityMetrics(
            entity_id=entity_id,
            entity_type=entity_type,
            entity_data=data,
        )

        metrics.total_fields = len(schema)
        required_count = sum(1 for f in schema if f.required)
        recommended_count = sum(1 for f in schema if not f.required)

        # Validate each field
        for field_rule in schema:
            field_name = field_rule.name
            field_value = data.get(field_name)

            # Check presence
            if field_rule.required and field_value is None:
                metrics.validation_errors.append(f"Required field missing: {field_name}")
            elif field_value is not None:
                # Field is present
                if field_rule.required:
                    metrics.required_fields_present += 1
                else:
                    metrics.recommended_fields_present += 1

                # Validate content
                validation_error = self._validate_field_value(field_name, field_value, field_rule)
                if validation_error:
                    metrics.validation_errors.append(validation_error)

        # Calculate scores
        metrics.completeness_score = self._calculate_completeness_score(
            metrics.required_fields_present,
            metrics.recommended_fields_present,
            required_count,
            recommended_count,
        )

        metrics.accuracy_score = self._calculate_accuracy_score(
            len(metrics.validation_errors), metrics.total_fields
        )

        metrics.overall_quality_score = (
            metrics.completeness_score * 0.6 + metrics.accuracy_score * 0.4
        )

        return metrics

    def _validate_field_value(
        self, field_name: str, value: Any, rule: FieldValidation
    ) -> Optional[str]:
        """
        Validate a field value.

        Args:
            field_name: Field name
            value: Field value
            rule: Validation rule

        Returns:
            Error message if validation fails, None otherwise
        """
        # Type check
        if not isinstance(value, rule.data_type):
            # Allow empty strings for optional fields
            if not (isinstance(value, str) and value == "" and not rule.required):
                return (
                    f"{field_name}: Expected {rule.data_type.__name__}, got {type(value).__name__}"
                )

        # Length checks for strings
        if isinstance(value, str):
            if rule.min_length and len(value) < rule.min_length:
                return f"{field_name}: Too short (min {rule.min_length} chars)"
            if rule.max_length and len(value) > rule.max_length:
                return f"{field_name}: Too long (max {rule.max_length} chars)"

        # Allowed values check
        if rule.allowed_values and value not in rule.allowed_values:
            return (
                f"{field_name}: Invalid value '{value}'. "
                f"Allowed: {', '.join(rule.allowed_values)}"
            )

        # URL validation
        if rule.validate_url and isinstance(value, str):
            if not (value.startswith("http://") or value.startswith("https://")):
                return f"{field_name}: Invalid URL format"

        return None

    def _calculate_completeness_score(
        self,
        required_present: int,
        recommended_present: int,
        total_required: int,
        total_recommended: int,
    ) -> float:
        """Calculate data completeness score."""
        if total_required == 0 and total_recommended == 0:
            return 0.0

        required_pct = (required_present / total_required * 100) if total_required > 0 else 0
        recommended_pct = (
            (recommended_present / total_recommended * 100) if total_recommended > 0 else 0
        )

        # 70% weight on required fields, 30% on recommended
        score = (required_pct * 0.7) + (recommended_pct * 0.3)
        return min(100.0, max(0.0, score))

    def _calculate_accuracy_score(self, error_count: int, field_count: int) -> float:
        """Calculate data accuracy score."""
        if field_count == 0:
            return 100.0
        # Each error reduces score by percentage of field count
        error_pct = (error_count / field_count) * 100
        score = 100.0 - error_pct
        return max(0.0, score)

    @staticmethod
    def _get_company_schema() -> List[FieldValidation]:
        """Get validation schema for company data."""
        return [
            # Required fields
            FieldValidation("name", required=True, data_type=str, min_length=2),
            FieldValidation(
                "website",
                required=True,
                data_type=str,
                validate_url=True,
            ),
            # Recommended fields
            FieldValidation("about", required=False, data_type=str),
            FieldValidation("techStack", required=False, data_type=list),
            FieldValidation("hasPortlandOffice", required=False, data_type=bool),
            FieldValidation(
                "tier",
                required=False,
                data_type=str,
                allowed_values=["S", "A", "B", "C", "D"],
            ),
            FieldValidation("priorityScore", required=False, data_type=int),
            # Optional fields
            FieldValidation("company_size_category", required=False, data_type=str),
            FieldValidation("headquarters_location", required=False, data_type=str),
        ]

    @staticmethod
    def _get_job_source_schema() -> List[FieldValidation]:
        """Get validation schema for job source data."""
        return [
            # Required fields
            FieldValidation("name", required=True, data_type=str, min_length=2),
            FieldValidation(
                "sourceType",
                required=True,
                data_type=str,
                allowed_values=["greenhouse", "rss", "api", "company-page", "workday"],
            ),
            FieldValidation("config", required=True, data_type=dict),
            FieldValidation("enabled", required=True, data_type=bool),
            # Recommended fields
            FieldValidation("companyId", required=False, data_type=str),
            FieldValidation("company_name", required=False, data_type=str),
            FieldValidation("tags", required=False, data_type=list),
            # Optional tracking fields
            FieldValidation("lastScrapedAt", required=False, data_type=str),
            FieldValidation("totalJobsFound", required=False, data_type=int),
            FieldValidation("totalJobsMatched", required=False, data_type=int),
        ]

    @staticmethod
    def _get_job_match_schema() -> List[FieldValidation]:
        """Get validation schema for job match data."""
        return [
            # Required fields
            FieldValidation("title", required=True, data_type=str, min_length=3),
            FieldValidation("company", required=True, data_type=str, min_length=2),
            FieldValidation("link", required=True, data_type=str, validate_url=True),
            # Recommended fields
            FieldValidation("description", required=False, data_type=str),
            FieldValidation("location", required=False, data_type=str),
            FieldValidation("companyId", required=False, data_type=str),
            FieldValidation("matchScore", required=False, data_type=float),
            FieldValidation("company_info", required=False, data_type=str),
            # Optional tracking fields
            FieldValidation("sourceId", required=False, data_type=str),
            FieldValidation("scrapedAt", required=False, data_type=str),
            FieldValidation("matchedAt", required=False, data_type=str),
            FieldValidation("urlHash", required=False, data_type=str),
        ]


def format_quality_report(report: TestDataQualityReport) -> str:
    """
    Format data quality report for display.

    Args:
        report: TestDataQualityReport to format

    Returns:
        Formatted report string
    """
    lines = [
        "",
        "═" * 80,
        "DATA QUALITY REPORT",
        "═" * 80,
        f"Test Run:          {report.test_run_id}",
        f"Duration:          {report.duration:.1f}s",
        "",
        "ENTITIES PROCESSED",
        "─" * 80,
        f"Companies:         {report.companies_processed}",
        f"Job Sources:       {report.sources_processed}",
        f"Job Matches:       {report.jobs_processed}",
        f"Total:             {report.total_entities}",
        "",
        "CREATED & IMPROVED",
        "─" * 80,
        f"New Companies:     {report.created_entities.get('company', 0)}",
        f"New Sources:       {report.created_entities.get('source', 0)}",
        f"New Jobs:          {report.created_entities.get('job', 0)}",
        f"Improved Companies: {report.improved_entities.get('company', 0)}",
        f"Improved Sources:  {report.improved_entities.get('source', 0)}",
        f"Improved Jobs:     {report.improved_entities.get('job', 0)}",
        "",
        "QUALITY METRICS",
        "─" * 80,
        f"Average Quality Score:     {report.average_quality_score:.1f}/100",
        f"Average Completeness:      {report.average_completeness_score:.1f}/100",
        f"Healthy Entities:          {report.healthy_entities}/{report.total_entities}",
        "",
        "DATA ISSUES",
        "─" * 80,
        f"Validation Errors:         {sum(report.errors_by_type.values())}",
        f"Data Issues:               {sum(report.issues_by_type.values())}",
    ]

    # Add error breakdown if present
    if report.errors_by_type:
        lines.append("  By Type:")
        for error_type, count in sorted(report.errors_by_type.items()):
            lines.append(f"    {error_type}: {count}")

    # Add issue breakdown if present
    if report.issues_by_type:
        lines.append("  Issues by Type:")
        for issue_type, count in sorted(report.issues_by_type.items()):
            lines.append(f"    {issue_type}: {count}")

    lines.extend(
        [
            "═" * 80,
            "",
        ]
    )

    return "\n".join(lines)
