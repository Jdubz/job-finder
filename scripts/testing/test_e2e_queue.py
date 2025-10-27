#!/usr/bin/env python3
# type: ignore
"""
End-to-end test for queue-based job processing pipeline.

⚠️ DEPRECATED: This script is deprecated in favor of the new scenario-based e2e tests
in tests/e2e/. Use those instead for better test coverage and maintainability.

See: tests/e2e/README.md for the new test suite.

This script tests the complete flow:
1. Scraper finds jobs → adds to queue
2. Queue processor picks up items (runs LOCALLY in this script - not realistic)
3. Company info is fetched
4. AI matching is performed
5. Results are stored in Firestore

Note: This script processes items locally instead of relying on the Portainer
staging worker like the new tests do. This is not representative of production.

Usage:
    python scripts/testing/test_e2e_queue.py

Recommended alternative:
    cd tests/e2e
    python run_all_scenarios.py
"""
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from job_finder.profile.firestore_loader import FirestoreProfileLoader  # noqa: E402
from job_finder.job_queue.manager import QueueManager  # noqa: E402
from job_finder.job_queue.models import QueueStatus  # noqa: E402
from job_finder.job_queue.scraper_intake import ScraperIntake  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_scraper_intake():
    """Test Phase 1: Scraper → Queue Intake."""
    print("\n" + "=" * 70)
    print("PHASE 1: Testing Scraper → Queue Intake")
    print("=" * 70 + "\n")

    # Initialize queue manager and intake
    queue_manager = QueueManager(database_name="portfolio-staging")
    intake = ScraperIntake(queue_manager)

    # Create sample jobs (simulating scraper output)
    sample_jobs = [
        {
            "url": "https://example.com/jobs/senior-python-engineer-test-1",
            "company": "Test Company A",
            "title": "Senior Python Engineer",
            "location": "Remote",
            "description": (
                "We are looking for a senior Python engineer "
                "with experience in Django, PostgreSQL, and AWS."
            ),
        },
        {
            "url": "https://example.com/jobs/fullstack-engineer-test-2",
            "company": "Test Company B",
            "title": "Full-Stack Engineer",
            "location": "Portland, OR",
            "description": (
                "Full-stack role working with React, TypeScript, Python, and Kubernetes."
            ),
        },
    ]

    print("Submitting test jobs to queue...")
    added_count = intake.submit_jobs(
        jobs=sample_jobs,
        source="e2e_test_scraper",
        company_id=None,
    )

    print(f"✓ Added {added_count} jobs to queue\n")

    # Verify jobs are in queue by querying directly without ordering
    # (Firestore composite index not required for this)
    from job_finder.job_queue.models import JobQueueItem
    from job_finder.storage.firestore_client import FirestoreClient

    db = FirestoreClient.get_client("portfolio-staging")
    collection = db.collection("job-queue")

    # Get all documents with our test source
    docs = collection.where("source", "==", "e2e_test_scraper").stream()

    test_items = []
    for doc in docs:
        data = doc.to_dict()
        item = JobQueueItem.from_firestore(doc.id, data)
        test_items.append(item)

    print("Verification:")
    print(f"  - Test items found: {len(test_items)}")

    for item in test_items:
        print(f"    • {item.company_name}: {item.url[:60]}...")

    if len(test_items) != added_count:
        print(f"\n⚠ WARNING: Expected {added_count} items, found {len(test_items)}")

    return test_items


def test_queue_processor(test_items):
    """Test Phase 2-4: Queue Processor → Company Info → AI Matching."""
    print("\n" + "=" * 70)
    print("PHASE 2-4: Testing Queue Processor → Company Info → AI Matching")
    print("=" * 70 + "\n")

    import yaml

    from job_finder.ai import AIJobMatcher
    from job_finder.company_info_fetcher import CompanyInfoFetcher
    from job_finder.job_queue.config_loader import ConfigLoader
    from job_finder.job_queue.processor import QueueItemProcessor
    from job_finder.storage import FirestoreJobStorage
    from job_finder.storage.companies_manager import CompaniesManager
    from job_finder.storage.firestore_client import FirestoreClient
    from job_finder.storage.job_sources_manager import JobSourcesManager

    # Load config file
    with open("config/config.yaml") as f:
        config = yaml.safe_load(f)

    # Load profile
    print("Loading user profile from Firestore...")
    profile_loader = FirestoreProfileLoader(database_name="portfolio-staging")
    profile = profile_loader.load_profile(name="Josh Wentworth")
    print(f"✓ Loaded profile for {profile.name}\n")

    # Initialize all components
    print("Initializing components...")
    database_name = "portfolio-staging"
    db = FirestoreClient.get_client(database_name)
    queue_manager = QueueManager(database_name=database_name)
    config_loader = ConfigLoader(database_name=database_name)
    job_storage = FirestoreJobStorage(db)
    companies_manager = CompaniesManager(database_name=database_name)
    sources_manager = JobSourcesManager(database_name=database_name)
    company_info_fetcher = CompanyInfoFetcher()

    # Create AI provider
    import os

    from job_finder.ai.providers import ClaudeProvider

    ai_config = config.get("ai", {})
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment")

    provider = ClaudeProvider(
        api_key=api_key, model=ai_config.get("model", "claude-3-5-haiku-20241022")
    )
    ai_matcher = AIJobMatcher(
        provider=provider,
        profile=profile,
        min_match_score=ai_config.get("min_match_score", 80),
        generate_intake=ai_config.get("generate_intake_data", True),
        portland_office_bonus=ai_config.get("portland_office_bonus", 15),
        user_timezone=ai_config.get("user_timezone", -8),
        prefer_large_companies=ai_config.get("prefer_large_companies", True),
    )

    # Create processor
    processor = QueueItemProcessor(
        queue_manager=queue_manager,
        config_loader=config_loader,
        job_storage=job_storage,
        companies_manager=companies_manager,
        sources_manager=sources_manager,
        company_info_fetcher=company_info_fetcher,
        ai_matcher=ai_matcher,
    )
    print("✓ Processor initialized\n")

    # Process the test items
    results = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }

    for item in test_items:
        if not item.id:
            print(f"⚠ Skipping item without ID: {item.url}")
            continue

        print(f"\nProcessing item: {item.id}")
        print(f"  Company: {item.company_name}")
        print(f"  URL: {item.url}")

        try:
            # Process the item
            processor.process_item(item)
            results["processed"] += 1

            # Check final status
            time.sleep(1)  # Give it a moment to update
            updated_item = processor.queue_manager.get_item(item.id)

            if updated_item:
                # Handle status as enum or string
                status_str = (
                    updated_item.status.value
                    if hasattr(updated_item.status, "value")
                    else updated_item.status
                )
                print(f"  Status: {status_str}")
                print(f"  Message: {updated_item.result_message or 'N/A'}")

                if updated_item.status == QueueStatus.SUCCESS or status_str == "success":
                    results["success"] += 1
                elif updated_item.status == QueueStatus.FAILED or status_str == "failed":
                    results["failed"] += 1
                elif updated_item.status == QueueStatus.SKIPPED or status_str == "skipped":
                    results["skipped"] += 1

        except Exception as e:
            print(f"  ✗ Error processing item: {e}")
            results["failed"] += 1

    print("\n" + "=" * 70)
    print("Processing Results:")
    print("=" * 70)
    print(f"  Processed: {results['processed']}")
    print(f"  Success:   {results['success']}")
    print(f"  Failed:    {results['failed']}")
    print(f"  Skipped:   {results['skipped']}")
    print("=" * 70)

    return results


def verify_firestore_results(test_items):
    """Test Phase 5: Verify Results in Firestore."""
    print("\n" + "=" * 70)
    print("PHASE 5: Verifying Results in Firestore")
    print("=" * 70 + "\n")

    from job_finder.storage.firestore_client import FirestoreClient

    db = FirestoreClient.get_client("portfolio-staging")

    # Get all matches
    matches_collection = db.collection("job-matches")
    all_docs = list(matches_collection.limit(100).stream())
    all_matches = [doc.to_dict() for doc in all_docs]

    # Find our test jobs
    test_urls = {item.url for item in test_items}
    test_matches = [match for match in all_matches if match.get("url") in test_urls]

    print(f"Found {len(test_matches)} test matches in job-matches collection\n")

    for match in test_matches:
        print("Job Match Found:")
        print(f"  Title: {match.get('title')}")
        print(f"  Company: {match.get('company')}")
        print(f"  Match Score: {match.get('matchScore')}")
        print(f"  Priority: {match.get('applicationPriority')}")
        print(f"  Has Resume Intake: {bool(match.get('resumeIntake'))}")
        print(f"  Has Company Info: {bool(match.get('companyInfo'))}")
        print()

    return test_matches


def cleanup_test_data(test_items):
    """Clean up test data from Firestore."""
    print("\n" + "=" * 70)
    print("Cleanup: Removing Test Data")
    print("=" * 70 + "\n")

    response = input("Remove test data from Firestore? (yes/no): ")
    if response.lower() != "yes":
        print("Skipped cleanup. Test data remains in Firestore.")
        return

    from job_finder.storage.firestore_client import FirestoreClient

    db = FirestoreClient.get_client("portfolio-staging")

    # Remove from queue
    for item in test_items:
        if item.id:
            try:
                db.collection("job-queue").document(item.id).delete()
                print(f"✓ Deleted queue item: {item.id}")
            except Exception as e:
                print(f"✗ Error deleting queue item {item.id}: {e}")

    # Remove from job-matches
    test_urls = {item.url for item in test_items}
    matches_collection = db.collection("job-matches")
    matches = matches_collection.stream()

    for match in matches:
        data = match.to_dict()
        if data.get("url") in test_urls:
            try:
                match.reference.delete()
                print(f"✓ Deleted job-match: {match.id}")
            except Exception as e:
                print(f"✗ Error deleting job-match {match.id}: {e}")

    print("\n✓ Cleanup complete")


def main():
    """Run end-to-end test."""
    print("\n" + "=" * 70)
    print("End-to-End Queue Processing Test")
    print("=" * 70)
    print("\nThis test will:")
    print("1. Add test jobs to the queue")
    print("2. Process them through the pipeline")
    print("3. Verify results in Firestore")
    print("4. Clean up test data")
    print("\nNote: This will use real AI API calls and may incur costs.")
    print("=" * 70 + "\n")

    response = input("Proceed with test? (yes/no): ")
    if response.lower() != "yes":
        print("Test aborted.")
        return

    try:
        # Phase 1: Scraper → Queue
        test_items = test_scraper_intake()

        if not test_items:
            print("\n✗ No test items created. Aborting test.")
            return

        # Phase 2-4: Queue Processor
        results = test_queue_processor(test_items)

        # Phase 5: Verify Firestore
        matches = verify_firestore_results(test_items)

        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Items created:       {len(test_items)}")
        print(f"Items processed:     {results['processed']}")
        print(f"Successful matches:  {results['success']}")
        print(f"Failed:              {results['failed']}")
        print(f"Skipped:             {results['skipped']}")
        print(f"Matches in Firestore: {len(matches)}")
        print("=" * 70)

        # Cleanup
        cleanup_test_data(test_items)

        print("\n✓ End-to-end test complete!")

    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
