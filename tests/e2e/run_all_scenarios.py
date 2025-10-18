#!/usr/bin/env python
"""
Run all E2E test scenarios.

This script runs all E2E scenarios and generates a summary report.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.scenarios import (
    TestResult,
    TestStatus,
    JobSubmissionScenario,
    FilteredJobScenario,
    CompanySourceDiscoveryScenario,
    ScrapeRotationScenario,
    FullDiscoveryCycleScenario,
)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def print_separator():
    """Print separator line."""
    print("=" * 80)


def print_summary(results: List[TestResult]):
    """
    Print test summary.

    Args:
        results: List of test results
    """
    print_separator()
    print("TEST SUMMARY")
    print_separator()

    total = len(results)
    passed = sum(1 for r in results if r.status == TestStatus.SUCCESS)
    failed = sum(1 for r in results if r.status == TestStatus.FAILURE)
    errors = sum(1 for r in results if r.status == TestStatus.ERROR)
    skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)

    total_duration = sum(r.duration for r in results)

    print(f"\nTotal scenarios: {total}")
    print(f"  ✓ Passed:  {passed}")
    print(f"  ✗ Failed:  {failed}")
    print(f"  ⚠ Errors:  {errors}")
    print(f"  ⊝ Skipped: {skipped}")
    print(f"\nTotal duration: {total_duration:.2f}s")

    # Detailed results
    if results:
        print("\nDetailed Results:")
        print("-" * 80)

        for result in results:
            status_symbol = {
                TestStatus.SUCCESS: "✓",
                TestStatus.FAILURE: "✗",
                TestStatus.ERROR: "⚠",
                TestStatus.SKIPPED: "⊝",
            }.get(result.status, "?")

            print(
                f"{status_symbol} {result.scenario_name}: "
                f"{result.status.value} ({result.duration:.2f}s)"
            )

            if result.status in [TestStatus.FAILURE, TestStatus.ERROR]:
                print(f"  Message: {result.message}")
                if result.error:
                    print(f"  Error: {result.error}")

    print_separator()

    # Exit code based on results
    return 0 if failed == 0 and errors == 0 else 1


def run_scenarios(
    database_name: str = "portfolio-staging",
    verbose: bool = False,
    cleanup: bool = True,
    scenarios: List[str] = None,
) -> List[TestResult]:
    """
    Run test scenarios.

    Args:
        database_name: Firestore database name
        verbose: Enable verbose logging
        cleanup: Clean up test data
        scenarios: List of scenario names to run (None = all)

    Returns:
        List of test results
    """
    # Define all available scenarios
    all_scenarios = {
        "job_submission": JobSubmissionScenario,
        "filtered_job": FilteredJobScenario,
        "company_source_discovery": CompanySourceDiscoveryScenario,
        "scrape_rotation": ScrapeRotationScenario,
        "full_discovery_cycle": FullDiscoveryCycleScenario,
    }

    # Determine which scenarios to run
    if scenarios:
        to_run = {k: v for k, v in all_scenarios.items() if k in scenarios}
        if not to_run:
            print(f"No matching scenarios found. Available: {list(all_scenarios.keys())}")
            return []
    else:
        to_run = all_scenarios

    print_separator()
    print(f"RUNNING {len(to_run)} E2E SCENARIO(S)")
    print(f"Database: {database_name}")
    print(f"Cleanup: {cleanup}")
    print_separator()

    results = []

    for scenario_name, scenario_class in to_run.items():
        print(f"\nRunning: {scenario_name}")
        print("-" * 80)

        try:
            scenario = scenario_class(
                database_name=database_name,
                verbose=verbose,
                cleanup=cleanup,
            )
            result = scenario.run()
            results.append(result)

        except Exception as e:
            print(f"✗ Unexpected error running {scenario_name}: {e}")
            logging.error(f"Error running scenario {scenario_name}", exc_info=True)

            # Create error result
            from tests.e2e.scenarios import TestResult, TestStatus

            result = TestResult(
                scenario_name=scenario_class.__name__,
                status=TestStatus.ERROR,
                duration=0.0,
                message=f"Runner error: {e}",
                error=e,
            )
            results.append(result)

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run E2E test scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all scenarios
  python run_all_scenarios.py

  # Run with verbose logging
  python run_all_scenarios.py --verbose

  # Run without cleanup (for debugging)
  python run_all_scenarios.py --no-cleanup

  # Run specific scenarios
  python run_all_scenarios.py --scenarios job_submission filtered_job

  # Run against production database (CAREFUL!)
  python run_all_scenarios.py --database portfolio
        """,
    )

    parser.add_argument(
        "--database",
        default="portfolio-staging",
        help="Firestore database name (default: portfolio-staging)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Do not clean up test data (for debugging)",
    )

    parser.add_argument(
        "--scenarios",
        nargs="+",
        help="Specific scenarios to run (default: all)",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List available scenarios and exit",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # List scenarios if requested
    if args.list:
        print("Available scenarios:")
        print("  - job_submission: Complete job submission flow")
        print("  - filtered_job: Job filtering and rejection")
        return 0

    # Run scenarios
    results = run_scenarios(
        database_name=args.database,
        verbose=args.verbose,
        cleanup=not args.no_cleanup,
        scenarios=args.scenarios,
    )

    # Print summary
    exit_code = print_summary(results)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
