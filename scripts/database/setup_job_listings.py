#!/usr/bin/env python3
"""Set up initial job listings in Firestore."""
import os

from dotenv import load_dotenv

from job_finder.storage import JobListingsManager

load_dotenv()

print("=" * 70)
print("JOB LISTINGS SETUP")
print("=" * 70)

# Initialize listings manager
# Use STORAGE_DATABASE_NAME env var if set, otherwise default to portfolio-staging
database_name = os.getenv("STORAGE_DATABASE_NAME", "portfolio-staging")
print(f"Using database: {database_name}")

manager = JobListingsManager(database_name=database_name)

print("\n📦 Adding scraper-friendly job sources...")
print("-" * 70)

# ============================================================================
# RSS FEEDS
# ============================================================================

# We Work Remotely - RSS Feed
listing_id = manager.add_listing(
    name="We Work Remotely - Programming",
    source_type="rss",
    config={
        "url": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "parse_format": "standard",
        "title_field": "title",
        "description_field": "description",
        "link_field": "link",
        "company_extraction": "from_title",  # Company name is in title
    },
    enabled=True,
    tags=["remote", "programming", "rss"],
)
print(f"✓ Added: We Work Remotely - Programming (ID: {listing_id})")

# We Work Remotely - Full Stack
listing_id = manager.add_listing(
    name="We Work Remotely - Full Stack",
    source_type="rss",
    config={
        "url": "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
        "parse_format": "standard",
        "title_field": "title",
        "description_field": "description",
        "link_field": "link",
        "company_extraction": "from_title",
    },
    enabled=True,
    tags=["remote", "full-stack", "rss"],
)
print(f"✓ Added: We Work Remotely - Full Stack (ID: {listing_id})")

# Remotive - Software Development
listing_id = manager.add_listing(
    name="Remotive - Software Development",
    source_type="rss",
    config={
        "url": "https://remotive.com/remote-jobs/software-dev/feed",
        "parse_format": "standard",
        "title_field": "title",
        "description_field": "description",
        "link_field": "link",
    },
    enabled=True,
    tags=["remote", "software", "rss"],
)
print(f"✓ Added: Remotive - Software Development (ID: {listing_id})")

# ============================================================================
# PUBLIC APIS
# ============================================================================

# RemoteOK API
listing_id = manager.add_listing(
    name="RemoteOK API",
    source_type="api",
    config={
        "base_url": "https://remoteok.com/api",
        "auth_type": "none",
        "endpoints": {"jobs": "/"},
        "params": {},
        "rate_limit": "300/day",  # Be respectful
        "response_format": "json",
        "filters": {"tags": ["dev", "engineering", "full-stack"]},
    },
    enabled=True,
    tags=["remote", "api"],
)
print(f"✓ Added: RemoteOK API (ID: {listing_id})")

# Adzuna API (requires API key)
listing_id = manager.add_listing(
    name="Adzuna Job Search API",
    source_type="api",
    config={
        "base_url": "https://api.adzuna.com/v1/api/jobs/us/search",
        "auth_type": "api_key",
        "api_key_env": "ADZUNA_APP_ID",  # Requires ADZUNA_APP_ID and ADZUNA_API_KEY
        "api_secret_env": "ADZUNA_API_KEY",
        "endpoints": {"search": "/1"},  # Page number
        "params": {
            "what": "software engineer",
            "where": "remote",
            "content-type": "application/json",
        },
        "rate_limit": "free tier",
        "response_format": "json",
    },
    enabled=False,  # Disabled until API keys are configured
    tags=["remote", "api", "requires-key"],
)
print(f"✓ Added: Adzuna API (ID: {listing_id}) - DISABLED (needs API key)")

# ============================================================================
# COMPANY CAREER PAGES
# ============================================================================

# Netflix
listing_id = manager.add_listing(
    name="Netflix Careers",
    source_type="company-page",
    config={
        "company_name": "Netflix",
        "careers_url": "https://explore.jobs.netflix.net/careers",
        "company_website": "https://www.netflix.com",
        "company_info": (
            "Netflix is the world's leading streaming entertainment service. "
            "Netflix culture emphasizes freedom and responsibility, with core "
            "values including judgment, communication, impact, curiosity, "
            "innovation, courage, passion, honesty, and selflessness."
        ),
        "method": "api",
        "api_endpoint": "https://explore.jobs.netflix.net/api/careers",
        "api_params": {"location": "Remote", "team": "Engineering"},
    },
    enabled=True,
    tags=["company-page", "remote", "big-tech"],
)
print(f"✓ Added: Netflix Careers (ID: {listing_id})")

# Shopify
listing_id = manager.add_listing(
    name="Shopify Careers",
    source_type="company-page",
    config={
        "company_name": "Shopify",
        "careers_url": "https://www.shopify.com/careers",
        "company_website": "https://www.shopify.com",
        "company_info": (
            "Shopify is a leading global commerce company, providing trusted "
            "tools to start, grow, market, and manage a retail business of any size."
        ),
        "method": "scraper",
        "selectors": {
            "job_list": ".job-listing",
            "title": ".job-title",
            "location": ".job-location",
            "department": ".job-department",
            "link": "a.job-link",
        },
        "filters": {"location": "Remote", "department": "Engineering"},
    },
    enabled=False,  # Disabled until scraper is implemented
    tags=["company-page", "remote", "ecommerce"],
)
print(f"✓ Added: Shopify Careers (ID: {listing_id}) - DISABLED (scraper not implemented)")

# Stripe
listing_id = manager.add_listing(
    name="Stripe Careers",
    source_type="company-page",
    config={
        "company_name": "Stripe",
        "careers_url": "https://stripe.com/jobs",
        "company_website": "https://stripe.com",
        "company_info": (
            "Stripe is a technology company that builds economic infrastructure "
            "for the internet. Businesses of every size use Stripe's software to "
            "accept payments and manage their businesses online."
        ),
        "method": "api",
        "api_endpoint": "https://stripe.com/jobs/search",
        "api_params": {"remote": "true"},
    },
    enabled=False,  # Disabled until API integration is implemented
    tags=["company-page", "remote", "fintech"],
)
print(f"✓ Added: Stripe Careers (ID: {listing_id}) - DISABLED (API not implemented)")

print("\n" + "=" * 70)
print("✅ JOB LISTINGS SETUP COMPLETE!")
print("=" * 70)
print("\nTo view active listings, query the 'job-listings' collection in Firestore.")
print("Database: portfolio-staging")
