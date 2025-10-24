#!/usr/bin/env python
"""Score job listing companies based on Portland offices and tech stack alignment.

This script calculates priority scores for all companies in the database and updates
their records with scoring information.

Usage:
    # Score companies in staging
    STORAGE_DATABASE_NAME=portfolio-staging python scripts/score_companies.py

    # Score companies in production
    STORAGE_DATABASE_NAME=portfolio python scripts/score_companies.py
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict

sys.path.insert(0, "src")

from dotenv import load_dotenv

from job_finder.storage.listings_manager import JobListingsManager

load_dotenv()

# Scoring weights
PORTLAND_OFFICE_BONUS = 50
TECH_STACK_POINTS = {
    "mongodb": 15,
    "redis": 15,
    "kubernetes": 10,
    "gcp": 10,
    "nodejs": 10,
    "typescript": 10,
    "angular": 10,
    "react": 8,
    "python": 8,
    "mysql": 8,
    "pubsub": 8,
    "docker": 5,
    "bullmq": 5,
}

COMPANY_TYPE_POINTS = {
    "remote_first": 15,
    "ai_ml_focus": 10,
    "distributed_systems": 5,
    "strong_eng_culture": 5,
}

# Company data with Portland presence and tech stacks
COMPANY_DATA = {
    "Coinbase Careers": {
        "has_portland_office": True,
        "tech_stack": ["typescript", "nodejs", "react", "python", "kubernetes", "docker"],
        "company_type": ["distributed_systems"],
        "notes": "Portland office opened 2018, secondary HQ",
    },
    "Cloudflare Careers": {
        "has_portland_office": True,  # Data center
        "tech_stack": ["typescript", "kubernetes", "docker"],
        "company_type": ["distributed_systems"],
        "notes": "Portland data center presence",
    },
    "MongoDB Careers": {
        "has_portland_office": False,
        "tech_stack": ["mongodb", "nodejs", "typescript", "python", "kubernetes", "gcp", "docker"],
        "company_type": ["remote_first", "distributed_systems"],
        "notes": "Perfect MongoDB match, remote positions",
    },
    "Redis Careers": {
        "has_portland_office": False,
        "tech_stack": ["redis", "nodejs", "typescript", "python", "kubernetes", "gcp", "docker"],
        "company_type": ["distributed_systems"],
        "notes": "Perfect Redis match",
    },
    "Datadog Careers": {
        "has_portland_office": False,
        "tech_stack": ["python", "kubernetes", "gcp", "docker"],
        "company_type": ["remote_first", "distributed_systems", "strong_eng_culture"],
        "notes": "Observability platform, global remote culture",
    },
    "Twilio Careers": {
        "has_portland_office": False,
        "tech_stack": ["nodejs", "typescript", "python", "kubernetes", "pubsub", "docker"],
        "company_type": ["remote_first", "distributed_systems"],
        "notes": "Communications APIs, Segment, remote-first",
    },
    "HashiCorp Careers": {
        "has_portland_office": False,
        "tech_stack": ["kubernetes", "gcp", "docker"],
        "company_type": ["remote_first", "distributed_systems", "strong_eng_culture"],
        "notes": "IaC tools, K8s/GCP focus",
    },
    "Scale AI Careers": {
        "has_portland_office": False,
        "tech_stack": ["python", "kubernetes", "docker"],
        "company_type": ["ai_ml_focus", "distributed_systems"],
        "notes": "Leading AI platform",
    },
    "Databricks Careers": {
        "has_portland_office": False,
        "tech_stack": ["python", "kubernetes", "docker"],
        "company_type": ["ai_ml_focus", "distributed_systems", "remote_first"],
        "notes": "Big data/AI platform",
    },
    "Stripe Careers": {
        "has_portland_office": False,
        "tech_stack": ["typescript", "react", "python", "kubernetes", "docker"],
        "company_type": ["distributed_systems", "strong_eng_culture"],
        "notes": "Payments infrastructure",
    },
    "GitLab Careers": {
        "has_portland_office": False,
        "tech_stack": ["typescript", "react", "python", "kubernetes", "gcp", "docker", "redis"],
        "company_type": ["remote_first", "distributed_systems"],
        "notes": "DevOps platform, fully remote",
    },
    "PagerDuty Careers": {
        "has_portland_office": False,
        "tech_stack": ["typescript", "python", "kubernetes", "docker"],
        "company_type": ["distributed_systems"],
        "notes": "Incident management",
    },
    "Grammarly Careers": {
        "has_portland_office": False,
        "tech_stack": ["typescript", "react", "python", "docker"],
        "company_type": ["ai_ml_focus"],
        "notes": "AI writing assistant",
    },
    "Brex Careers": {
        "has_portland_office": False,
        "tech_stack": ["typescript", "react", "python", "kubernetes", "docker"],
        "company_type": [],
        "notes": "Fintech",
    },
    "Waymo Careers": {
        "has_portland_office": False,
        "tech_stack": ["python", "kubernetes", "docker"],
        "company_type": ["ai_ml_focus", "distributed_systems"],
        "notes": "Autonomous vehicles (limited remote)",
    },
    # RSS and other sources - lower priority by default
    "We Work Remotely - Full Stack": {
        "has_portland_office": False,
        "tech_stack": [],
        "company_type": ["remote_first"],
        "notes": "Job board aggregator",
    },
    "We Work Remotely - Programming": {
        "has_portland_office": False,
        "tech_stack": [],
        "company_type": ["remote_first"],
        "notes": "Job board aggregator",
    },
    "Remotive - Software Development": {
        "has_portland_office": False,
        "tech_stack": [],
        "company_type": ["remote_first"],
        "notes": "Job board aggregator",
    },
    "Netflix Careers": {
        "has_portland_office": False,
        "tech_stack": ["react", "nodejs", "typescript", "python", "kubernetes", "docker"],
        "company_type": ["distributed_systems", "strong_eng_culture"],
        "notes": "Streaming platform",
    },
    "RemoteOK API": {
        "has_portland_office": False,
        "tech_stack": [],
        "company_type": ["remote_first"],
        "notes": "Job board aggregator",
    },
}


def calculate_company_score(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate priority score for a company.

    Args:
        company_data: Company configuration with tech stack and attributes

    Returns:
        Dictionary with score, tier, and scoring breakdown
    """
    score = 0
    scoring_factors = {}

    # Portland office bonus
    if company_data.get("has_portland_office", False):
        score += PORTLAND_OFFICE_BONUS
        scoring_factors["portland_office"] = PORTLAND_OFFICE_BONUS

    # Tech stack points
    tech_points = 0
    tech_breakdown = {}
    for tech in company_data.get("tech_stack", []):
        points = TECH_STACK_POINTS.get(tech, 0)
        if points > 0:
            tech_points += points
            tech_breakdown[tech] = points

    score += tech_points
    if tech_breakdown:
        scoring_factors["tech_stack"] = tech_breakdown
        scoring_factors["tech_stack_total"] = tech_points

    # Company type bonuses
    type_points = 0
    type_breakdown = {}
    for comp_type in company_data.get("company_type", []):
        points = COMPANY_TYPE_POINTS.get(comp_type, 0)
        if points > 0:
            type_points += points
            type_breakdown[comp_type] = points

    score += type_points
    if type_breakdown:
        scoring_factors["company_type"] = type_breakdown
        scoring_factors["company_type_total"] = type_points

    # Determine tier
    # Tier S: 100+ (Portland office + strong tech match)
    # Tier A: 70-99 (Perfect tech matches without Portland)
    # Tier B: 50-69 (Good matches)
    # Tier C: 30-49 (Moderate matches)
    # Tier D: 0-29 (Basic/job boards)
    if score >= 100:
        tier = "S"
    elif score >= 70:
        tier = "A"
    elif score >= 50:
        tier = "B"
    elif score >= 30:
        tier = "C"
    else:
        tier = "D"

    return {
        "priorityScore": score,
        "tier": tier,
        "scoringFactors": scoring_factors,
        "techStack": company_data.get("tech_stack", []),
        "hasPortlandOffice": company_data.get("has_portland_office", False),
        "scoringNotes": company_data.get("notes", ""),
    }


def main():
    database_name = os.getenv("STORAGE_DATABASE_NAME", "portfolio-staging")

    print("=" * 80)
    print(f"SCORING COMPANIES IN: {database_name}")
    print("=" * 80)
    print()

    manager = JobListingsManager(database_name=database_name)

    # Get all listings (enabled and disabled)
    all_listings = []
    for doc in manager.db.collection("job-listings").stream():
        listing = doc.to_dict()
        listing["id"] = doc.id
        all_listings.append(listing)

    print(f"📋 Found {len(all_listings)} total job listings")
    print()

    updated_count = 0
    skipped_count = 0

    # Track stats by tier
    tier_stats = {"S": [], "A": [], "B": [], "C": [], "D": []}

    for listing in all_listings:
        name = listing.get("name", "Unknown")
        doc_id = listing["id"]

        # Get company data
        company_data = COMPANY_DATA.get(name)

        if not company_data:
            print(f"⚠️  SKIPPED: {name} (no scoring data defined)")
            skipped_count += 1
            continue

        # Calculate score
        score_data = calculate_company_score(company_data)

        # Update Firestore
        manager.db.collection("job-listings").document(doc_id).update(
            {
                "priorityScore": score_data["priorityScore"],
                "tier": score_data["tier"],
                "scoringFactors": score_data["scoringFactors"],
                "techStack": score_data["techStack"],
                "hasPortlandOffice": score_data["hasPortlandOffice"],
                "scoringNotes": score_data["scoringNotes"],
                "scoredAt": datetime.now(),
            }
        )

        # Display result
        tier_icon = {"S": "⭐", "A": "🔷", "B": "🟢", "C": "🟡", "D": "⚪"}.get(
            score_data["tier"], "❓"
        )

        portland_icon = "🏙️ " if score_data["hasPortlandOffice"] else ""

        print(f"{tier_icon} {portland_icon}{name}")
        print(f'      Score: {score_data["priorityScore"]} | Tier {score_data["tier"]}')
        if score_data["hasPortlandOffice"]:
            print(f"      Portland Office: +{PORTLAND_OFFICE_BONUS}")
        if score_data["techStack"]:
            print(
                f'      Tech Stack: {", ".join(score_data["techStack"][:5])}{"..." if len(score_data["techStack"]) > 5 else ""}'
            )
        print(f'      Notes: {score_data["scoringNotes"]}')
        print(f"      ID: {doc_id}")
        print()

        updated_count += 1
        tier_stats[score_data["tier"]].append((name, score_data["priorityScore"]))

    print("=" * 80)
    print("✅ COMPANY SCORING COMPLETE")
    print("=" * 80)
    print(f"Database: {database_name}")
    print(f"Updated: {updated_count}")
    print(f"Skipped: {skipped_count}")
    print()

    # Display tier breakdown
    for tier in ["S", "A", "B", "C", "D"]:
        companies = tier_stats[tier]
        if companies:
            tier_name = {
                "S": "Perfect Match",
                "A": "Excellent Match",
                "B": "Good Match",
                "C": "Moderate Match",
                "D": "Basic Match",
            }[tier]

            print(f"Tier {tier} - {tier_name} ({len(companies)} companies):")
            # Sort by score descending
            companies.sort(key=lambda x: x[1], reverse=True)
            for name, score in companies:
                print(f"  {score:3d} - {name}")
            print()


if __name__ == "__main__":
    main()
