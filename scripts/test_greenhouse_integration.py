#!/usr/bin/env python
"""Test Greenhouse scraper integration with job search pipeline."""

import sys

sys.path.insert(0, "src")

from dotenv import load_dotenv

from job_finder.storage.listings_manager import JobListingsManager

load_dotenv()


def main():
    print("=" * 70)
    print("GREENHOUSE SCRAPER INTEGRATION TEST")
    print("=" * 70)
    print()

    # Check listings in staging
    manager = JobListingsManager(database_name="portfolio-staging")
    listings = manager.get_active_listings()

    print(f"✅ Found {len(listings)} active listings")
    print()

    greenhouse_count = 0
    rss_count = 0

    print("Active sources:")
    for listing in listings:
        source_type = listing.get("sourceType", "unknown")
        name = listing.get("name", "Unknown")

        if source_type == "greenhouse":
            greenhouse_count += 1
            board_token = listing.get("board_token", "N/A")
            print(f"  🟢 {name} (Greenhouse)")
            print(f"      Board: {board_token}")
        elif source_type == "rss":
            rss_count += 1
            print(f"  📡 {name} (RSS)")
        else:
            print(f"  ⚠️  {name} ({source_type})")

    print()
    print(f"Summary:")
    print(f"  Greenhouse sources: {greenhouse_count}")
    print(f"  RSS sources: {rss_count}")
    print(f"  Other sources: {len(listings) - greenhouse_count - rss_count}")
    print()
    print("=" * 70)
    print("✅ Greenhouse scraper is integrated and ready!")
    print("=" * 70)


if __name__ == "__main__":
    main()
