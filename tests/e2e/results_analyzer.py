"""
E2E Test Results Analyzer

Analyzes collected test data and generates comprehensive reports:
- Compares backup vs final Firestore state
- Tracks job submission patterns
- Measures data quality improvements
- Generates metrics for dashboard

Usage:
    python tests/e2e/results_analyzer.py \
        --results-dir ./test_results/run_001 \
        --output-dir ./reports
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CollectionComparison:
    """Comparison between two collection snapshots."""

    collection_name: str
    original_count: int
    final_count: int
    created_count: int = 0
    deleted_count: int = 0
    modified_count: int = 0

    @property
    def net_change(self) -> int:
        """Calculate net change."""
        return self.created_count - self.deleted_count

    @property
    def change_percentage(self) -> float:
        """Calculate percentage change."""
        if self.original_count == 0:
            return 100.0 if self.final_count > 0 else 0.0
        return ((self.final_count - self.original_count) / self.original_count) * 100


@dataclass
class JobSubmissionAnalysis:
    """Analysis of job submission results."""

    total_submitted: int
    total_succeeded: int
    total_failed: int
    submissions_by_status: Dict[str, int] = field(default_factory=dict)
    submissions_by_company: Dict[str, int] = field(default_factory=dict)
    avg_submission_duration: float = 0.0
    total_submission_duration: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_submitted == 0:
            return 0.0
        return (self.total_succeeded / self.total_submitted) * 100

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_submitted == 0:
            return 0.0
        return (self.total_failed / self.total_submitted) * 100


@dataclass
class TestRunAnalysis:
    """Complete analysis of a test run."""

    test_run_id: str
    timestamp: str
    duration_seconds: float

    # Backup comparison
    collection_comparisons: Dict[str, CollectionComparison] = field(default_factory=dict)

    # Job submission analysis
    submission_analysis: Optional[JobSubmissionAnalysis] = None

    # Quality metrics
    data_quality_before: float = 0.0  # From backup
    data_quality_after: float = 0.0  # From final state
    data_quality_improvement: float = 0.0

    # Overall assessment
    overall_health_score: float = 0.0
    assessment: str = ""  # PASS, WARN, FAIL
    key_findings: List[str] = field(default_factory=list)

    @property
    def total_documents_created(self) -> int:
        """Total documents created across all collections."""
        return sum(c.created_count for c in self.collection_comparisons.values())

    @property
    def total_documents_processed(self) -> int:
        """Total documents processed."""
        return sum(c.final_count for c in self.collection_comparisons.values())


class ResultsAnalyzer:
    """Analyzes E2E test results."""

    def __init__(self, results_dir: Path, output_dir: Path):
        """Initialize analyzer."""
        self.results_dir = Path(results_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load results
        self.test_result = self._load_test_result()
        self.backup_metadata = self._load_backup_metadata()
        self.backup_collections = self._load_backup_collections()
        self.final_collections = self._load_final_collections()

    def _load_test_result(self) -> Dict[str, Any]:
        """Load test_results.json."""
        results_file = self.results_dir / "test_results.json"
        if not results_file.exists():
            logger.warning(f"No test results found: {results_file}")
            return {}

        with open(results_file) as f:
            return json.load(f)

    def _load_backup_metadata(self) -> Dict[str, Any]:
        """Load backup_metadata.json."""
        metadata_file = self.results_dir / "backup_original" / "backup_metadata.json"
        if not metadata_file.exists():
            logger.warning(f"No backup metadata: {metadata_file}")
            return {}

        with open(metadata_file) as f:
            return json.load(f)

    def _load_backup_collections(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load backed up collections."""
        collections = {}
        backup_dir = self.results_dir / "backup_original"

        for json_file in backup_dir.glob("*.json"):
            if json_file.name == "backup_metadata.json":
                continue

            collection_name = json_file.stem
            with open(json_file) as f:
                collections[collection_name] = json.load(f)

        return collections

    def _load_final_collections(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load final collection snapshots."""
        collections = {}

        for json_file in self.results_dir.glob("final_*.json"):
            collection_name = json_file.stem.replace("final_", "")
            with open(json_file) as f:
                collections[collection_name] = json.load(f)

        return collections

    def analyze(self) -> TestRunAnalysis:
        """
        Perform complete analysis.

        Returns:
            TestRunAnalysis with all findings
        """
        analysis = TestRunAnalysis(
            test_run_id=self.test_result.get("test_run_id", "unknown"),
            timestamp=datetime.utcnow().isoformat(),
            duration_seconds=self.test_result.get("duration_seconds", 0.0),
        )

        # Analyze collection changes
        analysis.collection_comparisons = self._analyze_collection_changes()

        # Analyze job submissions
        analysis.submission_analysis = self._analyze_submissions()

        # Calculate quality improvements
        analysis.data_quality_before = self._calculate_quality(self.backup_collections)
        analysis.data_quality_after = self._calculate_quality(self.final_collections)
        analysis.data_quality_improvement = (
            analysis.data_quality_after - analysis.data_quality_before
        )

        # Generate assessment
        analysis = self._assess_results(analysis)

        return analysis

    def _analyze_collection_changes(
        self,
    ) -> Dict[str, CollectionComparison]:
        """
        Analyze changes in collections.

        Returns:
            Dictionary of collection comparisons
        """
        comparisons = {}

        # Get all collection names
        all_collections = set(self.backup_collections.keys()) | set(self.final_collections.keys())

        for collection_name in all_collections:
            backup_docs = self.backup_collections.get(collection_name, [])
            final_docs = self.final_collections.get(collection_name, [])

            comparison = CollectionComparison(
                collection_name=collection_name,
                original_count=len(backup_docs),
                final_count=len(final_docs),
            )

            # Calculate differences
            backup_ids = {d["id"] for d in backup_docs}
            final_ids = {d["id"] for d in final_docs}

            comparison.created_count = len(final_ids - backup_ids)
            comparison.deleted_count = len(backup_ids - final_ids)
            comparison.modified_count = len(final_ids & backup_ids)

            comparisons[collection_name] = comparison

        return comparisons

    def _analyze_submissions(self) -> JobSubmissionAnalysis:
        """
        Analyze job submissions.

        Returns:
            JobSubmissionAnalysis
        """
        submissions = self.test_result.get("submission_records", [])

        analysis = JobSubmissionAnalysis(
            total_submitted=self.test_result.get("jobs_submitted", 0),
            total_succeeded=self.test_result.get("jobs_succeeded", 0),
            total_failed=self.test_result.get("jobs_failed", 0),
        )

        # Analyze by status
        for submission in submissions:
            status = submission.get("actual_result", "unknown")
            analysis.submissions_by_status[status] = (
                analysis.submissions_by_status.get(status, 0) + 1
            )

            company = submission.get("company_name", "unknown")
            analysis.submissions_by_company[company] = (
                analysis.submissions_by_company.get(company, 0) + 1
            )

            analysis.total_submission_duration += submission.get("duration_seconds", 0.0)

        if analysis.total_submitted > 0:
            analysis.avg_submission_duration = (
                analysis.total_submission_duration / analysis.total_submitted
            )

        return analysis

    def _calculate_quality(self, collections: Dict[str, List[Dict[str, Any]]]) -> float:
        """
        Calculate data quality score.

        Args:
            collections: Collections to analyze

        Returns:
            Quality score (0-100)
        """
        if not collections:
            return 0.0

        total_score = 0.0
        collection_count = 0

        for collection_name, docs in collections.items():
            if not docs:
                continue

            collection_count += 1

            # Calculate completeness for this collection
            completeness = self._calculate_collection_completeness(collection_name, docs)

            total_score += completeness

        if collection_count == 0:
            return 0.0

        return total_score / collection_count

    def _calculate_collection_completeness(
        self, collection_name: str, docs: List[Dict[str, Any]]
    ) -> float:
        """Calculate completeness score for a collection."""
        if not docs:
            return 0.0

        # Define required and recommended fields by collection
        field_requirements = {
            "companies": {
                "required": ["id", "name", "website"],
                "recommended": ["about", "tier", "techStack"],
            },
            "job-sources": {
                "required": ["id", "name", "sourceType"],
                "recommended": ["config", "enabled"],
            },
            "job-matches": {
                "required": ["id", "title", "company", "link"],
                "recommended": ["description", "scrapedAt", "sourceId"],
            },
            "job-listings": {
                "required": ["id", "title", "company"],
                "recommended": ["description", "link"],
            },
            "job-queue": {
                "required": ["id", "status"],
                "recommended": ["createdAt", "startedAt", "completedAt"],
            },
        }

        requirements = field_requirements.get(
            collection_name,
            {"required": [], "recommended": []},
        )

        total_completeness = 0.0

        for doc in docs:
            # Check required fields
            required_present = sum(1 for field in requirements["required"] if field in doc)
            required_score = (
                (required_present / len(requirements["required"]))
                if requirements["required"]
                else 1.0
            )

            # Check recommended fields
            recommended_present = sum(1 for field in requirements["recommended"] if field in doc)
            recommended_score = (
                (recommended_present / len(requirements["recommended"]))
                if requirements["recommended"]
                else 1.0
            )

            # Combine: required is 70%, recommended is 30%
            doc_score = (required_score * 0.7) + (recommended_score * 0.3)
            total_completeness += doc_score

        return (total_completeness / len(docs)) * 100

    def _assess_results(self, analysis: TestRunAnalysis) -> TestRunAnalysis:
        """
        Assess overall test results.

        Args:
            analysis: Analysis to assess

        Returns:
            Updated analysis with assessment
        """
        findings = []

        # Check job submissions
        if analysis.submission_analysis:
            if analysis.submission_analysis.success_rate < 80:
                findings.append(
                    f"Low job submission success rate: {analysis.submission_analysis.success_rate:.1f}%"
                )
            elif analysis.submission_analysis.success_rate >= 95:
                findings.append(
                    f"Excellent job submission success: {analysis.submission_analysis.success_rate:.1f}%"
                )

        # Check collection growth
        documents_created = analysis.total_documents_created
        if documents_created == 0:
            findings.append("No new documents created")
        else:
            findings.append(f"Created {documents_created} new documents")

        # Check data quality
        if analysis.data_quality_after < 50:
            findings.append("Poor data quality in final state")
        elif analysis.data_quality_after >= 85:
            findings.append("Good data quality in final state")

        if analysis.data_quality_improvement > 10:
            findings.append(
                f"Significant quality improvement: +{analysis.data_quality_improvement:.1f}%"
            )

        # Calculate overall health score
        score = 50.0  # Base score

        if analysis.submission_analysis:
            score += analysis.submission_analysis.success_rate * 0.3

        score += min(analysis.data_quality_after / 100 * 20, 20)  # Up to 20 points

        score += min(documents_created, 10)  # Up to 10 points for documents created

        analysis.overall_health_score = min(score, 100.0)

        # Determine assessment
        if analysis.overall_health_score >= 80:
            analysis.assessment = "PASS"
        elif analysis.overall_health_score >= 60:
            analysis.assessment = "WARN"
        else:
            analysis.assessment = "FAIL"

        analysis.key_findings = findings
        return analysis

    def generate_report(self, analysis: TestRunAnalysis) -> str:
        """
        Generate human-readable report.

        Args:
            analysis: Analysis to report

        Returns:
            Report text
        """
        report = []

        report.append("E2E TEST RESULTS ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")

        # Header
        report.append(f"Test Run ID:        {analysis.test_run_id}")
        report.append(f"Analysis Time:      {analysis.timestamp}")
        report.append(f"Duration:           {analysis.duration_seconds:.1f}s")
        report.append(f"Assessment:         {analysis.assessment}")
        report.append(f"Health Score:       {analysis.overall_health_score:.1f}/100")
        report.append("")

        # Collection Changes
        report.append("COLLECTION CHANGES")
        report.append("-" * 80)
        for comp in analysis.collection_comparisons.values():
            report.append(
                f"{comp.collection_name:20} {comp.original_count:4} → "
                f"{comp.final_count:4} (+{comp.created_count}, -{comp.deleted_count}) "
                f"{comp.change_percentage:+.1f}%"
            )
        report.append("")

        # Job Submissions
        if analysis.submission_analysis:
            report.append("JOB SUBMISSIONS")
            report.append("-" * 80)
            sa = analysis.submission_analysis
            report.append(f"Total Submitted:    {sa.total_submitted}")
            report.append(f"Succeeded:          {sa.total_succeeded}")
            report.append(f"Failed:             {sa.total_failed}")
            report.append(f"Success Rate:       {sa.success_rate:.1f}%")
            report.append(f"Avg Duration:       {sa.avg_submission_duration:.2f}s")
            report.append("")

            if sa.submissions_by_status:
                report.append("By Status:")
                for status, count in sa.submissions_by_status.items():
                    report.append(f"  {status:20} {count:3}")
                report.append("")

        # Data Quality
        report.append("DATA QUALITY")
        report.append("-" * 80)
        report.append(f"Before:             {analysis.data_quality_before:.1f}/100")
        report.append(f"After:              {analysis.data_quality_after:.1f}/100")
        report.append(f"Improvement:        {analysis.data_quality_improvement:+.1f}%")
        report.append("")

        # Key Findings
        if analysis.key_findings:
            report.append("KEY FINDINGS")
            report.append("-" * 80)
            for finding in analysis.key_findings:
                report.append(f"  • {finding}")
            report.append("")

        # Summary
        report.append("=" * 80)
        report.append(f"Total Documents Processed: {analysis.total_documents_processed}")
        report.append(f"Total Documents Created:   {analysis.total_documents_created}")

        return "\n".join(report)

    def save_analysis(self, analysis: TestRunAnalysis) -> None:
        """
        Save analysis to files.

        Args:
            analysis: Analysis to save
        """
        # Save as JSON
        json_file = self.output_dir / "analysis.json"
        with open(json_file, "w") as f:
            json.dump(asdict(analysis), f, indent=2, default=str)
        logger.info(f"Saved analysis to {json_file}")

        # Save as text report
        report_file = self.output_dir / "report.txt"
        report_text = self.generate_report(analysis)
        with open(report_file, "w") as f:
            f.write(report_text)
        logger.info(f"Saved report to {report_file}")

        # Display report
        print("\n" + report_text + "\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze E2E test results")
    parser.add_argument(
        "--results-dir",
        required=True,
        help="Directory containing test results",
    )
    parser.add_argument(
        "--output-dir",
        default="./analysis_reports",
        help="Output directory for analysis (default: ./analysis_reports)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (default: False)",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Run analysis
    analyzer = ResultsAnalyzer(
        results_dir=args.results_dir,
        output_dir=args.output_dir,
    )

    analysis = analyzer.analyze()
    analyzer.save_analysis(analysis)


if __name__ == "__main__":
    main()
