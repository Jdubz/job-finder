#!/usr/bin/env python
"""Add Phase 1 Greenhouse companies to job listings database.

This script adds 13 high-priority Greenhouse companies identified in research.
Companies are added to the specified database (staging or production).

Usage:
    # Add to staging
    STORAGE_DATABASE_NAME=portfolio-staging python scripts/add_phase1_companies.py

    # Add to production
    STORAGE_DATABASE_NAME=portfolio python scripts/add_phase1_companies.py
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, "src")

from dotenv import load_dotenv

from job_finder.storage.listings_manager import JobListingsManager

load_dotenv()

# Phase 1 companies - all use Greenhouse ATS
PHASE1_COMPANIES = [
    {
        "name": "MongoDB Careers",
        "url": "https://boards.greenhouse.io/mongodb",
        "type": "greenhouse",
        "sourceType": "greenhouse",
        "board_token": "mongodb",
        "company_website": "https://www.mongodb.com",
        "enabled": True,  # Perfect tech match
        "priority": "HIGH",
        "notes": "Perfect match - MongoDB expertise, remote positions",
    },
    {
        "name": "Redis Careers",
        "url": "https://job-boards.greenhouse.io/redis",
        "type": "greenhouse",
        "sourceType": "greenhouse",
        "board_token": "redis",
        "company_website": "https://redis.io",
        "enabled": True,  # Perfect tech match
        "priority": "HIGH",
        "notes": "Perfect match - Redis expertise, in-memory database platform",
    },
    {
        "name": "Datadog Careers",
        "url": "https://boards.greenhouse.io/datadog",
        "type": "greenhouse",
        "sourceType": "greenhouse",
        "board_token": "datadog",
        "company_website": "https://www.datadoghq.com",
        "enabled": True,  # Remote-friendly + K8s match
        "priority": "HIGH",
        "notes": "Observability platform - K8s expert, global remote culture",
    },
    {
        "name": "Twilio Careers",
        "url": "https://job-boards.greenhouse.io/twilio",
        "type": "greenhouse",
        "sourceType": "greenhouse",
        "board_token": "twilio",
        "company_website": "https://www.twilio.com",
        "enabled": True,  # Remote-first company
        "priority": "HIGH",
        "notes": "Communications APIs, Segment - Node.js/TypeScript, remote-first",
    },
    {
        "name": "Cloudflare Careers",
        "url": "https://boards.greenhouse.io/cloudflare",
        "type": "greenhouse",
        "sourceType": "greenhouse",
        "board_token": "cloudflare",
        "company_website": "https://www.cloudflare.com",
        "enabled": True,  # Distributed systems
        "priority": "HIGH",
        "notes": "Edge computing, distributed systems, hybrid/remote",
    },
    {
        "name": "Scale AI Careers",
        "url": "https://job-boards.greenhouse.io/scaleai",
        "type": "greenhouse",
        "sourceType": "greenhouse",
        "board_token": "scaleai",
        "company_website": "https://scale.com",
        "enabled": True,  # Top AI company
        "priority": "HIGH",
        "notes": "Leading AI platform - Python/K8s, $168k-$300k",
    },
    {
        "name": "Databricks Careers",
        "url": "https://boards.greenhouse.io/databricks",
        "type": "greenhouse",
        "sourceType": "greenhouse",
        "board_token": "databricks",
        "company_website": "https://www.databricks.com",
        "enabled": True,  # Big data + AI + remote
        "priority": "HIGH",
        "notes": "Big data/AI platform - Python/K8s, many remote roles",
    },
    {
        "name": "HashiCorp Careers",
        "url": "https://boards.greenhouse.io/hashicorp",
        "type": "greenhouse",
        "sourceType": "greenhouse",
        "board_token": "hashicorp",
        "company_website": "https://www.hashicorp.com",
        "enabled": True,  # Perfect K8s/cloud match
        "priority": "HIGH",
        "notes": "IaC tools - K8s/GCP expert match, remote-friendly",
    },
    {
        "name": "Stripe Careers",
        "url": "https://boards.greenhouse.io/stripe",
        "type": "greenhouse",
        "sourceType": "greenhouse",
        "board_token": "stripe",
        "company_website": "https://stripe.com",
        "enabled": True,  # World-class eng culture
        "priority": "MEDIUM",
        "notes": "Payments infrastructure - TypeScript/React/Python",
    },
    {
        "name": "PagerDuty Careers",
        "url": "https://job-boards.greenhouse.io/pagerduty",
        "type": "greenhouse",
        "sourceType": "greenhouse",
        "board_token": "pagerduty",
        "company_website": "https://www.pagerduty.com",
        "enabled": False,  # Start disabled
        "priority": "MEDIUM",
        "notes": "Incident management - DevOps/SRE focus",
    },
    {
        "name": "Grammarly Careers",
        "url": "https://job-boards.greenhouse.io/grammarly",
        "type": "greenhouse",
        "sourceType": "greenhouse",
        "board_token": "grammarly",
        "company_website": "https://www.grammarly.com",
        "enabled": False,  # Start disabled
        "priority": "MEDIUM",
        "notes": "AI writing assistant - TypeScript/React/Python ML",
    },
    {
        "name": "Brex Careers",
        "url": "https://boards.greenhouse.io/brex",
        "type": "greenhouse",
        "sourceType": "greenhouse",
        "board_token": "brex",
        "company_website": "https://www.brex.com",
        "enabled": False,  # Start disabled
        "priority": "MEDIUM",
        "notes": "Fintech - TypeScript/React/Python/K8s",
    },
    {
        "name": "Waymo Careers",
        "url": "https://boards.greenhouse.io/waymo",
        "type": "greenhouse",
        "sourceType": "greenhouse",
        "board_token": "waymo",
        "company_website": "https://waymo.com",
        "enabled": False,  # Start disabled (limited remote)
        "priority": "MEDIUM",
        "notes": "Autonomous vehicles - Google-scale ML/AI (limited remote)",
    },
]


def main():
    database_name = os.getenv("STORAGE_DATABASE_NAME", "portfolio-staging")

    print("=" * 80)
    print(f"ADDING PHASE 1 GREENHOUSE COMPANIES TO: {database_name}")
    print("=" * 80)
    print()

    manager = JobListingsManager(database_name=database_name)

    # Get existing listings to check for duplicates
    existing_listings = manager.get_active_listings()
    disabled_listings = list(
        manager.db.collection("job-listings").where("enabled", "==", False).stream()
    )

    # Extract names from active listings (already dicts)
    existing_names = {listing.get("name") for listing in existing_listings}
    # Extract names from disabled listings (need to convert)
    existing_names.update({listing.to_dict().get("name") for listing in disabled_listings})

    print(f"📋 Found {len(existing_names)} existing job listings")
    print()

    added_count = 0
    skipped_count = 0
    enabled_count = 0

    for company in PHASE1_COMPANIES:
        name = company["name"]
        enabled = company["enabled"]
        priority = company["priority"]

        if name in existing_names:
            print(f"⏭️  SKIPPED: {name} (already exists)")
            skipped_count += 1
            continue

        # Create listing data
        listing_data = {
            "name": name,
            "url": company["url"],
            "type": company["type"],
            "sourceType": company["sourceType"],
            "board_token": company["board_token"],
            "company_website": company["company_website"],
            "enabled": enabled,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "lastScraped": None,
            "scrapeStatus": "pending",
            "jobsFound": 0,
            "jobsMatched": 0,
        }

        # Add to Firestore
        doc_ref = manager.db.collection("job-listings").add(listing_data)
        doc_id = doc_ref[1].id

        status_icon = "✅" if enabled else "⚪"
        priority_icon = "⭐" if priority == "HIGH" else "🔷"

        print(f"{status_icon} {priority_icon} ADDED: {name}")
        print(f'      Board: {company["board_token"]}')
        print(f"      Priority: {priority}")
        print(f"      Enabled: {enabled}")
        print(f'      Notes: {company["notes"]}')
        print(f"      ID: {doc_id}")
        print()

        added_count += 1
        if enabled:
            enabled_count += 1

    print("=" * 80)
    print("✅ PHASE 1 COMPANIES ADDED")
    print("=" * 80)
    print(f"Database: {database_name}")
    print(f"Added: {added_count}")
    print(f"Skipped (duplicates): {skipped_count}")
    print(f"Enabled: {enabled_count}")
    print(f"Disabled: {added_count - enabled_count}")
    print()
    print("Enabled companies (will be scraped on next run):")
    for company in PHASE1_COMPANIES:
        if company["enabled"]:
            print(f'  ✅ {company["name"]} ({company["board_token"]})')
    print()
    print("Disabled companies (can enable later):")
    for company in PHASE1_COMPANIES:
        if not company["enabled"]:
            print(f'  ⚪ {company["name"]} ({company["board_token"]})')
    print()


if __name__ == "__main__":
    main()
