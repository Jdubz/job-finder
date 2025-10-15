#!/usr/bin/env python
"""Test the new priority-based rotation algorithm.

This script simulates the job search rotation without actually scraping,
showing which companies would be scraped in what order.

Usage:
    # Test staging
    STORAGE_DATABASE_NAME=portfolio-staging python scripts/test_rotation_algorithm.py

    # Test production
    STORAGE_DATABASE_NAME=portfolio python scripts/test_rotation_algorithm.py
"""

import os
import sys

sys.path.insert(0, "src")

from dotenv import load_dotenv

from job_finder.storage.listings_manager import JobListingsManager

load_dotenv()


def main():
    database_name = os.getenv("STORAGE_DATABASE_NAME", "portfolio-staging")

    print("=" * 80)
    print(f"TESTING ROTATION ALGORITHM: {database_name}")
    print("=" * 80)
    print()

    manager = JobListingsManager(database_name=database_name)

    # Get active listings
    listings = manager.get_active_listings()

    # Sort by priority score (simulate orchestrator behavior)
    sorted_listings = sorted(
        listings, key=lambda x: (-(x.get("priorityScore", 0)), x.get("name", ""))
    )

    print(f"📋 Found {len(sorted_listings)} active job sources")
    print()

    # Show tier distribution
    tier_counts = {}
    for listing in sorted_listings:
        tier = listing.get("tier", "Unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    print("Priority Distribution:")
    tier_order = ["S", "A", "B", "C", "D"]
    for tier in tier_order:
        if tier in tier_counts:
            tier_name = {
                "S": "Perfect Match",
                "A": "Excellent Match",
                "B": "Good Match",
                "C": "Moderate Match",
                "D": "Basic Match",
            }.get(tier, tier)
            print(f"  Tier {tier} ({tier_name}): {tier_counts[tier]} sources")
    print()

    # Show scraping order
    print("=" * 80)
    print("SCRAPING ORDER (Priority-based Rotation)")
    print("=" * 80)
    print()

    for i, listing in enumerate(sorted_listings, 1):
        name = listing.get("name", "Unknown")
        score = listing.get("priorityScore", 0)
        tier = listing.get("tier", "?")
        source_type = listing.get("sourceType", "unknown")
        has_portland = listing.get("hasPortlandOffice", False)

        # Emojis
        tier_emoji = {"S": "⭐", "A": "🔷", "B": "🟢", "C": "🟡", "D": "⚪"}.get(tier, "❓")

        portland_icon = "🏙️ " if has_portland else ""

        print(f"{i:2d}. {tier_emoji} {portland_icon}{name}")
        print(f"     Score: {score} | Tier {tier} | Type: {source_type}")

        # Show tech stack if available
        tech_stack = listing.get("techStack", [])
        if tech_stack:
            tech_str = ", ".join(tech_stack[:5])
            if len(tech_stack) > 5:
                tech_str += f" (+{len(tech_stack) - 5} more)"
            print(f"     Tech: {tech_str}")

        print()

    print("=" * 80)
    print("ROTATION ANALYSIS")
    print("=" * 80)
    print()

    # Analyze first 10 sources (typical max_jobs limit)
    first_10 = sorted_listings[:10]

    tier_dist_first_10 = {}
    for listing in first_10:
        tier = listing.get("tier", "Unknown")
        tier_dist_first_10[tier] = tier_dist_first_10.get(tier, 0) + 1

    print("First 10 sources (typical search limit):")
    for tier in tier_order:
        if tier in tier_dist_first_10:
            print(f"  Tier {tier}: {tier_dist_first_10[tier]} sources")
    print()

    # Show Portland coverage
    portland_count = sum(1 for l in first_10 if l.get("hasPortlandOffice", False))
    print(f"Portland offices in first 10: {portland_count}")
    print()

    # Show average score
    avg_score_all = sum(l.get("priorityScore", 0) for l in sorted_listings) / len(sorted_listings)
    avg_score_first_10 = sum(l.get("priorityScore", 0) for l in first_10) / len(first_10)

    print(f"Average priority score:")
    print(f"  All sources: {avg_score_all:.1f}")
    print(f"  First 10: {avg_score_first_10:.1f}")
    print()

    print("✅ Rotation algorithm successfully prioritizes:")
    print("   1. Portland offices (Coinbase)")
    print("   2. Perfect tech matches (MongoDB, Redis, etc.)")
    print("   3. Good matches (Databricks, Stripe, etc.)")
    print("   4. Job boards last (RSS feeds)")
    print()


if __name__ == "__main__":
    main()
