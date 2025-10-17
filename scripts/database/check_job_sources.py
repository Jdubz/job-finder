#!/usr/bin/env python3
"""Check job sources in Firestore production database."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from job_finder.storage.firestore_client import FirestoreClient

# Set credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    ".firebase/static-sites-257923-firebase-adminsdk.json"
)

print("=" * 70)
print("CHECKING JOB SOURCES IN PRODUCTION DATABASE")
print("=" * 70)

# Get production database
db = FirestoreClient.get_client("portfolio")

# Query job-sources collection
sources_ref = db.collection("job-sources")
sources = list(sources_ref.stream())

print(f"\nTotal job sources: {len(sources)}")
print()

if len(sources) == 0:
    print("⚠️  NO JOB SOURCES FOUND!")
    print()
    print("This is why the scheduler found 0 sources to scrape.")
    print()
    print("Action needed:")
    print("  1. Run migration script to create job sources from listings")
    print("  2. Or manually create job sources in Firestore")
    print()
    sys.exit(1)

# Display sources
enabled_count = 0
disabled_count = 0

for doc in sources:
    data = doc.to_dict()
    source_id = doc.id
    name = data.get("name", "Unknown")
    source_type = data.get("sourceType", "unknown")
    enabled = data.get("enabled", False)
    company_id = data.get("companyId")
    company_name = data.get("companyName", "N/A")

    status = "✅ ENABLED" if enabled else "❌ DISABLED"

    if enabled:
        enabled_count += 1
    else:
        disabled_count += 1

    print(f"{status} - {name}")
    print(f"  ID: {source_id}")
    print(f"  Type: {source_type}")
    print(f"  Company: {company_name} ({company_id or 'no ID'})")
    print()

print("=" * 70)
print(f"Summary: {enabled_count} enabled, {disabled_count} disabled")
print("=" * 70)

if enabled_count == 0:
    print()
    print("⚠️  ALL SOURCES ARE DISABLED!")
    print()
    print("This is why the scheduler found 0 sources to scrape.")
    print()
    print("Action needed:")
    print("  Enable sources in Firestore or via migration script")
    print()
    sys.exit(1)

print()
print("✅ Job sources configured correctly")
