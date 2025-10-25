#!/usr/bin/env python3
"""
Migration Test Script

Tests the Phase 1 migration scripts on local Firebase emulator:
1. Creates test data (companies and job-sources without status fields)
2. Runs migration 001 (company status) in dry-run mode
3. Runs migration 001 in execute mode
4. Verifies company status fields
5. Runs migration 002 (source status) in dry-run mode
6. Runs migration 002 in execute mode
7. Verifies source status fields

Usage:
    # Make sure Firebase emulator is running on port 8080
    firebase emulators:start --only firestore

    # Run test
    FIRESTORE_EMULATOR_HOST=localhost:8080 python scripts/database/test_migrations.py
"""

import os
import sys
import subprocess
from datetime import datetime

from google.cloud import firestore

# Ensure we're connecting to emulator
if "FIRESTORE_EMULATOR_HOST" not in os.environ:
    print("ERROR: FIRESTORE_EMULATOR_HOST environment variable not set")
    print("Start emulator with: firebase emulators:start --only firestore")
    sys.exit(1)

print(f"✓ Connecting to Firestore emulator at {os.environ['FIRESTORE_EMULATOR_HOST']}")

# Connect to emulator
db = firestore.Client(database="(default)", project="static-sites-257923")


def create_test_data():
    """Create test data without status fields (pre-migration state)."""
    print("\n" + "=" * 60)
    print("Creating test data...")
    print("=" * 60)

    # Create 3 test companies WITHOUT status fields
    companies_data = [
        {
            "name": "Test Company 1",
            "name_lower": "test company 1",
            "name_normalized": "test-company-1",
            "website": "https://testcompany1.com",
            "about": "A great company to work for",
            "culture": "Collaborative and innovative",
            "mission": "Making the world better",
            "size": "100-500",
            "company_size_category": "medium",
            "headquarters_location": "Portland, OR",
            "industry": "Technology",
            "founded": "2015",
            "hasPortlandOffice": True,
            "techStack": ["Python", "React"],
            "tier": "A",
            "priorityScore": 120,
            "createdAt": datetime.now(),
            "updatedAt": datetime.now(),
            # NOTE: No 'status' or 'last_analyzed_at' fields
        },
        {
            "name": "Test Company 2",
            "name_lower": "test company 2",
            "name_normalized": "test-company-2",
            "website": "https://testcompany2.com",
            "about": "Another great company",
            "createdAt": datetime.now(),
            "updatedAt": datetime.now(),
            # NOTE: No 'status' or 'last_analyzed_at' fields
        },
        {
            "name": "Test Company 3",
            "name_lower": "test company 3",
            "name_normalized": "test-company-3",
            "website": "https://testcompany3.com",
            "createdAt": datetime.now(),
            # NOTE: No 'updatedAt', 'status', or 'last_analyzed_at' fields
        },
    ]

    for company in companies_data:
        ref = db.collection("companies").add(company)
        print(f"  Created company: {company['name']} (ID: {ref[1].id})")

    # Create 3 test job sources WITHOUT status fields
    sources_data = [
        {
            "name": "Test Source 1 - Enabled",
            "url": "https://boards.greenhouse.io/test1",
            "sourceType": "greenhouse",
            "enabled": True,  # Old field - should map to status="active"
            "config": {
                "api_token": "test123"
            },
            "createdAt": datetime.now(),
            "updatedAt": datetime.now(),
            # NOTE: No 'status', 'consecutiveFailures', or 'autoEnabled' fields
        },
        {
            "name": "Test Source 2 - Disabled",
            "url": "https://example.com/careers",
            "sourceType": "scraper",
            "enabled": False,  # Old field - should map to status="disabled"
            "config": {
                "selectors": {}
            },
            "createdAt": datetime.now(),
            "updatedAt": datetime.now(),
            # NOTE: No 'status', 'consecutiveFailures', or 'autoEnabled' fields
        },
        {
            "name": "Test Source 3 - No enabled field",
            "url": "https://example.com/rss",
            "sourceType": "rss",
            # NOTE: No 'enabled' field at all - should default to status="disabled"
            "config": {},
            "createdAt": datetime.now(),
            # NOTE: No 'status', 'consecutiveFailures', or 'autoEnabled' fields
        },
    ]

    for source in sources_data:
        ref = db.collection("job-sources").add(source)
        print(f"  Created source: {source['name']} (ID: {ref[1].id})")

    print(f"\n✓ Created {len(companies_data)} companies and {len(sources_data)} job sources")

    # Give the emulator a moment to persist the data
    import time
    time.sleep(1)

    # Verify data was created
    company_count = len(list(db.collection("companies").stream()))
    source_count = len(list(db.collection("job-sources").stream()))
    print(f"✓ Verified: {company_count} companies and {source_count} sources in database")


def run_migration(script_name: str, dry_run: bool = True) -> int:
    """Run a migration script."""
    mode = "--dry-run" if dry_run else "--execute"
    mode_label = "DRY RUN" if dry_run else "EXECUTE"

    print("\n" + "=" * 60)
    print(f"Running {script_name} ({mode_label})")
    print("=" * 60)

    cmd = [
        "python",
        f"scripts/database/{script_name}",
        "--database", "(default)",
        mode
    ]

    # Add --yes flag for non-interactive execution
    if not dry_run:
        cmd.append("--yes")

    # Set environment to use emulator
    env = os.environ.copy()
    result = subprocess.run(cmd, env=env)

    return result.returncode


def verify_companies():
    """Verify companies have status fields."""
    print("\n" + "=" * 60)
    print("Verifying companies collection...")
    print("=" * 60)

    docs = db.collection("companies").stream()

    all_valid = True
    for doc in docs:
        data = doc.to_dict()
        company_name = data.get("name", "Unknown")

        # Check for required fields
        has_status = "status" in data
        has_last_analyzed = "last_analyzed_at" in data

        if has_status and has_last_analyzed:
            print(f"  ✓ {company_name}: status={data['status']}, last_analyzed_at={data['last_analyzed_at']}")
        else:
            print(f"  ✗ {company_name}: Missing fields (status={has_status}, last_analyzed_at={has_last_analyzed})")
            all_valid = False

    return all_valid


def verify_sources():
    """Verify job-sources have status fields."""
    print("\n" + "=" * 60)
    print("Verifying job-sources collection...")
    print("=" * 60)

    docs = db.collection("job-sources").stream()

    all_valid = True
    for doc in docs:
        data = doc.to_dict()
        source_name = data.get("name", "Unknown")

        # Check for required fields
        has_status = "status" in data
        has_consecutive_failures = "consecutiveFailures" in data
        has_auto_enabled = "autoEnabled" in data

        if has_status and has_consecutive_failures and has_auto_enabled:
            print(f"  ✓ {source_name}: status={data['status']}, consecutiveFailures={data['consecutiveFailures']}, autoEnabled={data['autoEnabled']}")
        else:
            missing = []
            if not has_status:
                missing.append("status")
            if not has_consecutive_failures:
                missing.append("consecutiveFailures")
            if not has_auto_enabled:
                missing.append("autoEnabled")

            print(f"  ✗ {source_name}: Missing fields: {', '.join(missing)}")
            all_valid = False

    return all_valid


def cleanup_test_data():
    """Clean up test data."""
    print("\n" + "=" * 60)
    print("Cleaning up test data...")
    print("=" * 60)

    # Delete all companies
    companies = db.collection("companies").stream()
    for doc in companies:
        doc.reference.delete()
        print(f"  Deleted company: {doc.id}")

    # Delete all sources
    sources = db.collection("job-sources").stream()
    for doc in sources:
        doc.reference.delete()
        print(f"  Deleted source: {doc.id}")

    print("✓ Cleanup complete")


def main():
    """Run full migration test."""
    print("=" * 60)
    print("MIGRATION TEST SCRIPT")
    print(f"Emulator: {os.environ.get('FIRESTORE_EMULATOR_HOST')}")
    print("=" * 60)

    try:
        # 1. Create test data
        create_test_data()

        # 2. Run company migration (001) - dry run
        returncode = run_migration("001_add_company_status.py", dry_run=True)
        if returncode != 0:
            print(f"\n✗ Migration 001 dry-run failed with code {returncode}")
            return 1

        # 3. Run company migration (001) - execute
        returncode = run_migration("001_add_company_status.py", dry_run=False)
        if returncode != 0:
            print(f"\n✗ Migration 001 execution failed with code {returncode}")
            return 1

        # 4. Verify companies
        if not verify_companies():
            print("\n✗ Company verification failed")
            return 1

        # 5. Run source migration (002) - dry run
        returncode = run_migration("002_add_source_status.py", dry_run=True)
        if returncode != 0:
            print(f"\n✗ Migration 002 dry-run failed with code {returncode}")
            return 1

        # 6. Run source migration (002) - execute
        returncode = run_migration("002_add_source_status.py", dry_run=False)
        if returncode != 0:
            print(f"\n✗ Migration 002 execution failed with code {returncode}")
            return 1

        # 7. Verify sources
        if not verify_sources():
            print("\n✗ Source verification failed")
            return 1

        # 8. Success!
        print("\n" + "=" * 60)
        print("✅ ALL MIGRATIONS PASSED")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Clean up test data
        cleanup_test_data()


if __name__ == "__main__":
    sys.exit(main())
