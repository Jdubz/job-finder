#!/usr/bin/env python3
# type: ignore
"""
Clean up messy job-matches records in Firestore.

Issues to fix:
1. Empty company info
2. Missing fields (salary, location, etc.)
3. Duplicate job postings
4. Invalid match scores

SAFETY: Requires explicit --database flag and --allow-production to modify production.
"""
import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent / "src"))

from job_finder.storage.firestore_client import FirestoreClient  # noqa: E402
from job_finder.utils.url_utils import normalize_url  # noqa: E402


def analyze_job_matches(db, database_name: str):  # type: ignore[no-untyped-def]
    """Analyze job-matches for data quality issues."""
    print(f"\nAnalyzing job-matches in {database_name}...\n")

    collection = db.collection("job-matches")
    docs = list(collection.stream())

    print(f"Total job-matches: {len(docs)}\n")

    # Track various issues
    issues = {
        "missing_company": 0,
        "missing_company_website": 0,
        "empty_company_info": 0,
        "missing_description": 0,
        "missing_location": 0,
        "invalid_match_score": 0,
        "missing_url": 0,
        "duplicate_urls": {},
    }

    for doc in docs:
        data = doc.to_dict()

        # Check for missing/empty fields
        if not data.get("company"):
            issues["missing_company"] += 1

        if not data.get("companyWebsite"):
            issues["missing_company_website"] += 1

        if not data.get("companyInfo") or data.get("companyInfo", "").strip() == "":
            issues["empty_company_info"] += 1

        if not data.get("description"):
            issues["missing_description"] += 1

        if not data.get("location") or data.get("location") == "Unknown":
            issues["missing_location"] += 1

        # Check match score
        match_score = data.get("matchScore")
        if match_score is not None and (match_score < 0 or match_score > 100):
            issues["invalid_match_score"] += 1

        # Check for missing URL
        url = data.get("url")
        if not url:
            issues["missing_url"] += 1
        else:
            # Normalize URL for consistent duplicate detection
            normalized_url = normalize_url(url)
            # Track duplicates by normalized URL
            if normalized_url in issues["duplicate_urls"]:
                issues["duplicate_urls"][normalized_url].append(doc.id)
            else:
                issues["duplicate_urls"][normalized_url] = [doc.id]

    # Count actual duplicates (URLs with >1 record)
    duplicate_count = sum(1 for ids in issues["duplicate_urls"].values() if len(ids) > 1)

    # Print report
    print("=" * 70)
    print("Data Quality Report")
    print("=" * 70)
    print(f"Missing company name:        {issues['missing_company']}")
    print(f"Missing company website:     {issues['missing_company_website']}")
    print(f"Empty company info:          {issues['empty_company_info']}")
    print(f"Missing description:         {issues['missing_description']}")
    print(f"Missing/Unknown location:    {issues['missing_location']}")
    print(f"Invalid match scores:        {issues['invalid_match_score']}")
    print(f"Missing URL:                 {issues['missing_url']}")
    print(f"Duplicate URLs:              {duplicate_count}")
    print("=" * 70)

    # Show sample of duplicates
    if duplicate_count > 0:
        print("\nSample duplicate URLs:")
        count = 0
        for url, doc_ids in issues["duplicate_urls"].items():
            if len(doc_ids) > 1:
                print(f"\n  URL: {url[:80]}...")
                print(f"  Document IDs: {', '.join(doc_ids)}")
                count += 1
                if count >= 3:  # Show first 3
                    break

    return issues


def cleanup_duplicates(db, database_name: str):  # type: ignore[no-untyped-def]
    """Remove duplicate job postings (keep the one with most data)."""
    print(f"\n\nCleaning up duplicates in {database_name}...\n")

    collection = db.collection("job-matches")
    docs = list(collection.stream())

    # Group by normalized URL (handles historical data with non-normalized URLs)
    jobs_by_url: Dict[str, List[tuple]] = {}
    for doc in docs:
        data = doc.to_dict()
        url = data.get("url")
        if url:
            # Normalize URL to ensure consistent grouping
            normalized_url = normalize_url(url)
            if normalized_url not in jobs_by_url:
                jobs_by_url[normalized_url] = []
            jobs_by_url[normalized_url].append((doc.id, data))

    # Find and remove duplicates
    deleted_count = 0
    for url, records in jobs_by_url.items():
        if len(records) <= 1:
            continue

        print(f"\nDuplicate found: {url[:60]}...")
        print(f"  {len(records)} copies")

        # Score each record by completeness
        scored_records = []
        for doc_id, data in records:
            # Count non-empty fields
            score = sum(
                1
                for key in [
                    "company",
                    "companyWebsite",
                    "companyInfo",
                    "description",
                    "location",
                    "salary",
                ]
                if data.get(key) and str(data.get(key)).strip()
            )

            # Prefer records with resume intake data
            if data.get("resumeIntake"):
                score += 10

            # Prefer records with higher match scores
            if data.get("matchScore"):
                score += data.get("matchScore") / 10

            scored_records.append((score, doc_id, data))

        # Sort by score (descending)
        scored_records.sort(reverse=True, key=lambda x: x[0])

        # Keep the best one, delete others
        keep_id = scored_records[0][1]
        delete_ids = [doc_id for _, doc_id, _ in scored_records[1:]]

        print(f"  Keeping: {keep_id} (score: {scored_records[0][0]})")
        print(f"  Deleting: {len(delete_ids)} duplicates")

        for doc_id in delete_ids:
            collection.document(doc_id).delete()
            deleted_count += 1
            print(f"    ✓ Deleted: {doc_id}")

    print(f"\n{'=' * 70}")
    print(f"Deleted {deleted_count} duplicate job-matches")
    print("=" * 70)

    return deleted_count


def main():
    """Main cleanup function with production safety checks."""
    parser = argparse.ArgumentParser(
        description="Clean up job-matches duplicates in Firestore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Safe - clean staging only
  python scripts/database/cleanup_job_matches.py --database portfolio-staging
  
  # Blocked - production requires flag
  python scripts/database/cleanup_job_matches.py --database portfolio
  
  # Dangerous - explicit production override
  python scripts/database/cleanup_job_matches.py --database portfolio --allow-production
        """,
    )
    parser.add_argument(
        "--database",
        required=True,
        choices=["portfolio-staging", "portfolio"],
        help="Database to clean (use portfolio-staging for safety)",
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="DANGER: Allow production database modification (not recommended)",
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze issues, don't delete anything",
    )

    args = parser.parse_args()

    # SAFETY CHECK: Prevent accidental production usage
    if args.database == "portfolio" and not args.allow_production:
        print("=" * 80)
        print("🚨 PRODUCTION DATABASE BLOCKED 🚨")
        print("=" * 80)
        print("")
        print("This script would DELETE DUPLICATE RECORDS from production!")
        print("Database specified: portfolio (PRODUCTION)")
        print("")
        print("This script is designed for staging only.")
        print("Use --database portfolio-staging instead.")
        print("")
        print("If you REALLY need to run on production (not recommended):")
        print(
            "  python scripts/database/cleanup_job_matches.py --database portfolio --allow-production"
        )
        print("")
        print("=" * 80)
        sys.exit(1)

    # Warning for production usage
    if args.database == "portfolio":
        print("=" * 80)
        print("⚠️  RUNNING ON PRODUCTION DATABASE ⚠️")
        print("=" * 80)
        print("This will DELETE DUPLICATE job-matches from production!")
        print("Press Ctrl+C within 10 seconds to abort...")
        print("=" * 80)
        time.sleep(10)

    print("\n" + "=" * 70)
    print(f"Job-Matches Cleanup - {args.database}")
    print("=" * 70)

    # Connect to specified database
    db = FirestoreClient.get_client(args.database)

    # Analyze
    print(f"\n### Analyzing {args.database} ###")
    issues = analyze_job_matches(db, args.database)

    if args.analyze_only:
        print("\n" + "=" * 70)
        print("Analysis complete (no changes made)")
        print("=" * 70)
        return

    # Clean up duplicates
    print("\n" + "=" * 70)
    print("Cleanup Actions")
    print("=" * 70)
    print(f"\n### Cleaning {args.database} ###")
    deleted = cleanup_duplicates(db, args.database)

    # Final summary
    print("\n" + "=" * 70)
    print("Cleanup Complete!")
    print("=" * 70)
    print(f"\nDuplicates removed from {args.database}: {deleted}")

    print("\nRemaining data quality issues:")
    print(f"  - Empty company info: {issues['empty_company_info']}")
    print(f"  - Missing locations:  {issues['missing_location']}")

    print("\nNote: These remaining issues require company info fetcher to resolve.")


if __name__ == "__main__":
    main()
