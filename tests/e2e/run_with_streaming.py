"""
Example: Integrating Log Streaming and Data Quality Monitoring with E2E Tests

This example shows how to add real-time log streaming and data quality monitoring
to your E2E test runner. Tests now improve the tool and validate data accuracy.
"""

import os
import uuid
from contextlib import nullcontext

from tests.e2e.helpers import (
    LogStreamer,
    get_test_logs_summary,
    DataQualityMonitor,
    format_quality_report,
)
from tests.e2e.scenarios import (
    JobSubmissionScenario,
    FilteredJobScenario,
    CompanySourceDiscoveryScenario,
    ScrapeRotationScenario,
    FullDiscoveryCycleScenario,
)


def run_e2e_with_streaming(
    database_name: str = "portfolio-staging",
    verbose: bool = False,
    stream_logs: bool = True,
    monitor_quality: bool = True,
    scenarios=None,
):
    """
    Run E2E tests with real-time log streaming and data quality monitoring.

    Args:
        database_name: Firestore database to test
        verbose: Enable verbose output
        stream_logs: Enable real-time log streaming from Google Cloud Logs
        monitor_quality: Enable data quality monitoring
        scenarios: Specific scenarios to run (default: all)

    Returns:
        Dictionary with test results
    """

    # Generate test run ID
    test_run_id = f"e2e_test_{uuid.uuid4().hex[:8]}"

    print(f"\n{'='*80}")
    print(f"E2E Test Suite - {database_name}")
    print(f"Test Run ID: {test_run_id}")
    print(f"Log Streaming: {'ENABLED' if stream_logs else 'DISABLED'}")
    print(f"Data Quality Monitoring: {'ENABLED' if monitor_quality else 'DISABLED'}")
    print(f"{'='*80}\n")

    # Initialize data quality monitor
    quality_monitor = None
    if monitor_quality:
        quality_monitor = DataQualityMonitor()
        quality_monitor.start_test_run(test_run_id)

    # Get project ID from environment
    project_id = os.getenv("GCP_PROJECT_ID", "")
    if stream_logs and not project_id:
        print("⚠️  WARNING: GCP_PROJECT_ID not set. Disabling log streaming.")
        stream_logs = False

    # Set up log streaming context manager
    if stream_logs:
        try:
            log_streamer = LogStreamer(project_id, database_name)
            log_context = log_streamer.stream_logs(test_run_id=test_run_id)
        except Exception as e:
            print(f"⚠️  Could not initialize log streaming: {e}")
            log_context = nullcontext()
    else:
        log_context = nullcontext()

    # Define scenarios
    scenario_classes = [
        JobSubmissionScenario,
        FilteredJobScenario,
        CompanySourceDiscoveryScenario,
        ScrapeRotationScenario,
        FullDiscoveryCycleScenario,
    ]

    if scenarios:
        # Filter to requested scenarios
        scenario_names = {s.__name__: s for s in scenario_classes}
        scenario_classes = [scenario_names[s] for s in scenarios if s in scenario_names]

    # Run scenarios with log streaming and data quality monitoring
    results = []

    with log_context:
        print("\n" + "─" * 80)
        print("RUNNING SCENARIOS")
        print("─" * 80 + "\n")

        for scenario_class in scenario_classes:
            scenario_name = scenario_class.__name__
            print(f"\n▶ Starting: {scenario_name}")
            print("  " + "─" * 76)

            try:
                scenario = scenario_class(
                    database_name=database_name,
                    verbose=verbose,
                    cleanup=True,
                )

                # Inject test run ID and quality monitor for logging
                scenario.test_run_id = test_run_id
                scenario.quality_monitor = quality_monitor

                # Run scenario
                start_time = __import__("time").time()
                scenario.setup()
                scenario.execute()
                scenario.verify()
                scenario.cleanup()
                end_time = __import__("time").time()

                duration = end_time - start_time
                results.append(
                    {
                        "scenario": scenario_name,
                        "status": "success",
                        "duration": duration,
                    }
                )

                print(f"✓ PASSED in {duration:.1f}s")

            except AssertionError as e:
                results.append(
                    {
                        "scenario": scenario_name,
                        "status": "failure",
                        "error": str(e),
                    }
                )
                print(f"✗ FAILED: {e}")

            except Exception as e:
                results.append(
                    {
                        "scenario": scenario_name,
                        "status": "error",
                        "error": str(e),
                    }
                )
                print(f"⚠ ERROR: {e}")

    # Print summary
    print("\n" + "─" * 80)
    print("TEST SUMMARY")
    print("─" * 80)

    passed = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failure")
    errors = sum(1 for r in results if r["status"] == "error")
    total_duration = sum(r.get("duration", 0) for r in results)

    print(f"\nResults:")
    print(f"  ✓ Passed:  {passed}")
    print(f"  ✗ Failed:  {failed}")
    print(f"  ⚠ Errors:  {errors}")
    print(f"  Total time: {total_duration:.1f}s\n")

    for result in results:
        status_symbol = {
            "success": "✓",
            "failure": "✗",
            "error": "⚠",
        }.get(result["status"])

        line = f"{status_symbol} {result['scenario']}: {result['status']}"
        if result.get("duration"):
            line += f" ({result['duration']:.1f}s)"
        if result.get("error"):
            line += f" - {result['error'][:60]}"

        print(line)

    # Get and display log summary
    if stream_logs and project_id:
        print("\n" + "─" * 80)
        print("LOG SUMMARY")
        print("─" * 80 + "\n")

        try:
            summary = get_test_logs_summary(project_id, test_run_id)

            print(f"Total log entries: {summary['total_entries']}")
            print(
                f"Duration: {summary['duration']:.1f}s" if summary["duration"] else "Duration: N/A"
            )
            print(f"By severity: {summary['by_severity']}")
            print(f"By stage: {summary['by_stage']}")

            if summary["errors"]:
                print(f"\nErrors ({len(summary['errors'])}):")
                for error in summary["errors"][:3]:
                    print(f"  - {error['message'][:70]}")
                if len(summary["errors"]) > 3:
                    print(f"  ... and {len(summary['errors']) - 3} more")

            if summary["warnings"]:
                print(f"\nWarnings ({len(summary['warnings'])}):")
                for warning in summary["warnings"][:3]:
                    print(f"  - {warning['message'][:70]}")
                if len(summary["warnings"]) > 3:
                    print(f"  ... and {len(summary['warnings']) - 3} more")

        except Exception as e:
            print(f"Could not retrieve log summary: {e}")

    # Display data quality report
    if quality_monitor:
        quality_report = quality_monitor.end_test_run()
        print(format_quality_report(quality_report))

        # Print quality metrics summary
        summary = quality_monitor.get_report_summary()
        print("DATA QUALITY METRICS")
        print("─" * 80)
        print(f"Entities Processed:  {summary['entities_processed']['total']}")
        print(f"  Companies: {summary['entities_processed']['companies']}")
        print(f"  Sources:   {summary['entities_processed']['sources']}")
        print(f"  Jobs:      {summary['entities_processed']['jobs']}")
        print()
        print(f"Created/Improved:")
        print(f"  New Companies: {summary['created_entities'].get('company', 0)}")
        print(f"  New Sources:   {summary['created_entities'].get('source', 0)}")
        print(f"  New Jobs:      {summary['created_entities'].get('job', 0)}")
        print()
        print(f"Quality Scores:")
        print(f"  Average Quality:      {summary['quality_scores']['average']:.1f}/100")
        print(
            f"  Average Completeness: {summary['quality_scores']['average_completeness']:.1f}/100"
        )
        print(
            f"  Healthy Entities:     {summary['quality_scores']['healthy_entities']}/{summary['entities_processed']['total']}"
        )
        print()
        if summary["issues"]["validation_errors"] > 0 or summary["issues"]["data_issues"] > 0:
            print(f"Data Issues:")
            print(f"  Validation Errors: {summary['issues']['validation_errors']}")
            print(f"  Data Issues:       {summary['issues']['data_issues']}")

    print("\n" + "=" * 80)

    # Return exit code
    return 0 if (failed == 0 and errors == 0) else 1


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run E2E tests with real-time log streaming")
    parser.add_argument(
        "--database",
        default="portfolio-staging",
        help="Firestore database name (default: portfolio-staging)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file for test results (optional)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output (default: False)",
    )
    parser.add_argument(
        "--stream-logs",
        action="store_true",
        default=True,
        help="Enable log streaming from Google Cloud Logs (default: True)",
    )
    parser.add_argument(
        "--no-logs",
        action="store_true",
        help="Disable log streaming (overrides --stream-logs)",
    )
    parser.add_argument(
        "--monitor-quality",
        action="store_true",
        default=True,
        help="Enable data quality monitoring (default: True)",
    )
    parser.add_argument(
        "--no-quality",
        action="store_true",
        help="Disable data quality monitoring (overrides --monitor-quality)",
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        help="Specific scenarios to run (optional)",
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Allow running on production database (USE WITH EXTREME CAUTION)",
    )

    args = parser.parse_args()

    # SAFETY CHECK: Prevent accidental production usage
    if args.database == "portfolio" and not args.allow_production:
        print("=" * 80)
        print("🚨 PRODUCTION DATABASE BLOCKED 🚨")
        print("=" * 80)
        print("")
        print("This test would RUN SCENARIOS on the production database!")
        print("Database specified: portfolio (PRODUCTION)")
        print("")
        print("This test is designed for staging only.")
        print("Use --database portfolio-staging instead.")
        print("")
        print("If you REALLY need to run on production (not recommended):")
        print("  python tests/e2e/run_with_streaming.py --database portfolio --allow-production")
        print("")
        print("=" * 80)
        sys.exit(1)

    # Warning for production usage
    if args.database == "portfolio":
        print("=" * 80)
        print("⚠️  RUNNING ON PRODUCTION DATABASE ⚠️")
        print("=" * 80)
        print("This will RUN TEST SCENARIOS on production!")
        print("Press Ctrl+C within 10 seconds to abort...")
        print("=" * 80)
        import time

        time.sleep(10)

    # Handle logging preference
    stream_logs = not args.no_logs and (args.stream_logs or not args.no_logs)
    monitor_quality = not args.no_quality and (args.monitor_quality or not args.no_quality)

    output_file = None
    if args.output:
        import sys

        output_file = open(args.output, "w")
        sys.stdout = output_file
        sys.stderr = output_file

    try:
        exit_code = run_e2e_with_streaming(
            database_name=args.database,
            verbose=args.verbose,
            stream_logs=stream_logs,
            monitor_quality=monitor_quality,
            scenarios=args.scenarios,
        )
    finally:
        if output_file:
            output_file.close()

    exit(exit_code)
