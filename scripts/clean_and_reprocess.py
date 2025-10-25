#!/usr/bin/env python3
"""
Clean staging database and reprocess all jobs with new strike-based filters.

This script:
1. Backs up current job-matches to a JSON file
2. Clears job-matches and queue collections in staging
3. Reprocesses all backed up jobs through the new filter engine
4. Shows before/after statistics
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from job_finder.filters.strike_filter_engine import StrikeFilterEngine
from job_finder.storage.firestore_client import FirestoreClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_NAME = "portfolio-staging"
CREDENTIALS_PATH = ".firebase/static-sites-257923-firebase-adminsdk.json"
BACKUP_DIR = Path("data/backups")


# Filter configurations (from scoring script)
DEFAULT_FILTER_CONFIG = {
    "enabled": True,
    "strikeThreshold": 5,
    "hardRejections": {
        "excludedJobTypes": [
            "sales",
            "hr",
            "human resources",
            "people operations",
            "talent acquisition",
            "recruiter",
            "recruiting",
            "support",
            "customer success",
        ],
        "excludedSeniority": [
            "associate",
            "junior",
            "intern",
            "entry-level",
            "entry level",
            "co-op",
        ],
        "excludedCompanies": [],
        "excludedKeywords": [
            "clearance required",
            "security clearance",
            "relocation required",
            "must relocate",
        ],
        "minSalaryFloor": 100000,
        "rejectCommissionOnly": True,
    },
    "remotePolicy": {"allowRemote": True, "allowHybridPortland": True, "allowOnsite": False},
    "salaryStrike": {"enabled": True, "threshold": 150000, "points": 2},
    "experienceStrike": {"enabled": True, "minPreferred": 6, "points": 1},
    "seniorityStrikes": {
        "mid-level": 2,
        "mid level": 2,
        "principal": 1,
        "director": 1,
        "manager": 1,
        "engineering manager": 1,
    },
    "qualityStrikes": {
        "minDescriptionLength": 200,
        "shortDescriptionPoints": 1,
        "buzzwords": ["rockstar", "ninja", "guru", "10x engineer", "code wizard"],
        "buzzwordPoints": 1,
    },
    "ageStrike": {
        "enabled": True,
        "strikeDays": 1,
        "rejectDays": 7,
        "points": 1,
    },
}

DEFAULT_TECH_RANKS = {
    "technologies": {
        # Required (must have at least one)
        "Python": {"rank": "required", "points": 0, "mentions": 0},
        "TypeScript": {"rank": "required", "points": 0, "mentions": 0},
        "JavaScript": {"rank": "required", "points": 0, "mentions": 0},
        "React": {"rank": "required", "points": 0, "mentions": 0},
        "Angular": {"rank": "required", "points": 0, "mentions": 0},
        "Node.js": {"rank": "required", "points": 0, "mentions": 0},
        "GCP": {"rank": "required", "points": 0, "mentions": 0},
        "Google Cloud": {"rank": "required", "points": 0, "mentions": 0},
        "Kubernetes": {"rank": "required", "points": 0, "mentions": 0},
        "Docker": {"rank": "required", "points": 0, "mentions": 0},
        # OK (neutral)
        "C++": {"rank": "ok", "points": 0, "mentions": 0},
        "Go": {"rank": "ok", "points": 0, "mentions": 0},
        "Rust": {"rank": "ok", "points": 0, "mentions": 0},
        "PostgreSQL": {"rank": "ok", "points": 0, "mentions": 0},
        "MySQL": {"rank": "ok", "points": 0, "mentions": 0},
        "MongoDB": {"rank": "ok", "points": 0, "mentions": 0},
        "Redis": {"rank": "ok", "points": 0, "mentions": 0},
        # Strike (prefer to avoid)
        "Java": {"rank": "strike", "points": 2, "mentions": 0},
        "PHP": {"rank": "strike", "points": 2, "mentions": 0},
        "Ruby": {"rank": "strike", "points": 2, "mentions": 0},
        "Rails": {"rank": "strike", "points": 2, "mentions": 0},
        "Ruby on Rails": {"rank": "strike", "points": 2, "mentions": 0},
        "WordPress": {"rank": "strike", "points": 2, "mentions": 0},
        ".NET": {"rank": "strike", "points": 2, "mentions": 0},
        "C#": {"rank": "strike", "points": 2, "mentions": 0},
        "Perl": {"rank": "strike", "points": 2, "mentions": 0},
    },
    "strikes": {"missingAllRequired": 1, "perBadTech": 2},
}


class DatabaseCleaner:
    """Clean and reprocess staging database with new filters."""

    def __init__(self):
        """Initialize with Firestore client."""
        self.db = FirestoreClient.get_client(DATABASE_NAME, CREDENTIALS_PATH)
        self.filter_engine = StrikeFilterEngine(DEFAULT_FILTER_CONFIG, DEFAULT_TECH_RANKS)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    def backup_current_data(self) -> Dict[str, Any]:
        """
        Backup current job-matches to JSON file.

        Returns:
            Dictionary with backed up data
        """
        logger.info("Backing up current job-matches...")

        docs = list(self.db.collection("job-matches").stream())
        jobs = []

        for doc in docs:
            data = doc.to_dict()
            data["_doc_id"] = doc.id  # Preserve document ID
            jobs.append(data)

        backup_data = {
            "backup_timestamp": datetime.utcnow().isoformat(),
            "database": DATABASE_NAME,
            "total_jobs": len(jobs),
            "jobs": jobs,
        }

        # Save backup
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"job_matches_backup_{timestamp}.json"

        with open(backup_file, "w") as f:
            json.dump(backup_data, f, indent=2, default=str)

        logger.info(f"Backed up {len(jobs)} jobs to: {backup_file}")
        return backup_data

    def clear_collections(self):
        """Clear job-matches and job-queue collections."""
        logger.info("Clearing collections...")

        # Clear job-matches
        batch = self.db.batch()
        count = 0
        for doc in self.db.collection("job-matches").stream():
            batch.delete(doc.reference)
            count += 1
            if count % 500 == 0:
                batch.commit()
                batch = self.db.batch()

        if count % 500 != 0:
            batch.commit()
        logger.info(f"Deleted {count} job-matches")

        # Clear job-queue
        batch = self.db.batch()
        count = 0
        for doc in self.db.collection("job-queue").stream():
            batch.delete(doc.reference)
            count += 1
            if count % 500 == 0:
                batch.commit()
                batch = self.db.batch()

        if count % 500 != 0:
            batch.commit()
        logger.info(f"Deleted {count} queue items")

    def reprocess_jobs(self, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reprocess jobs through new filter engine.

        Args:
            backup_data: Backed up job data

        Returns:
            Statistics about reprocessing
        """
        logger.info("Reprocessing jobs with new filters...")

        jobs = backup_data["jobs"]
        stats = {
            "total": len(jobs),
            "passed": 0,
            "filtered": 0,
            "hard_rejected": 0,
            "strike_rejected": 0,
            "passed_jobs": [],
            "rejection_reasons": {},
        }

        batch = self.db.batch()
        batch_count = 0

        for job in jobs:
            # Prepare job data for filtering
            job_data = {
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "description": job.get("description", ""),
                "location": job.get("location", ""),
                "salary": job.get("salary", ""),
                "posted_date": job.get("postedDate"),
                "url": job.get("url", ""),
            }

            # Run filter
            result = self.filter_engine.evaluate_job(job_data)

            if result.passed:
                # Job passed - add back to job-matches
                stats["passed"] += 1
                stats["passed_jobs"].append(
                    {
                        "title": job_data["title"],
                        "company": job_data["company"],
                        "strikes": result.total_strikes,
                    }
                )

                # Remove backup metadata before saving
                job_copy = job.copy()
                job_copy.pop("_doc_id", None)

                # Add filter metadata
                job_copy["filter_result"] = {
                    "strikes": result.total_strikes,
                    "threshold": result.strike_threshold,
                    "passed": True,
                }

                # Add back to collection
                doc_ref = self.db.collection("job-matches").document()
                batch.set(doc_ref, job_copy)
                batch_count += 1

                if batch_count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()
                    batch_count = 0

            else:
                # Job filtered out
                stats["filtered"] += 1

                # Track rejection reasons
                if result.rejections:
                    # Check if hard rejected
                    has_hard_reject = any(r.severity == "hard_reject" for r in result.rejections)
                    if has_hard_reject:
                        stats["hard_rejected"] += 1
                    else:
                        stats["strike_rejected"] += 1

                    # Track reasons
                    for rejection in result.rejections:
                        reason = rejection.reason
                        if reason not in stats["rejection_reasons"]:
                            stats["rejection_reasons"][reason] = 0
                        stats["rejection_reasons"][reason] += 1

        # Commit remaining batch
        if batch_count > 0:
            batch.commit()

        logger.info(
            f"Reprocessing complete: {stats['passed']}/{stats['total']} jobs passed "
            f"({stats['passed']/stats['total']*100:.1f}%)"
        )

        return stats

    def run(self):
        """Run full clean and reprocess operation."""
        logger.info("=" * 80)
        logger.info("CLEAN AND REPROCESS STAGING DATABASE")
        logger.info("=" * 80)

        # Step 1: Backup
        backup_data = self.backup_current_data()
        original_count = backup_data["total_jobs"]

        # Step 2: Clear
        self.clear_collections()

        # Step 3: Reprocess
        stats = self.reprocess_jobs(backup_data)

        # Step 4: Report
        print("\n" + "=" * 80)
        print("REPROCESSING SUMMARY")
        print("=" * 80)
        print(f"\nOriginal jobs: {original_count}")
        print(f"Jobs after filtering: {stats['passed']}")
        print(f"Jobs removed: {stats['filtered']} ({stats['filtered']/original_count*100:.1f}%)")
        print(f"\nRejection Breakdown:")
        print(f"  Hard rejected: {stats['hard_rejected']}")
        print(f"  Strike rejected: {stats['strike_rejected']}")

        print(f"\nTop Rejection Reasons:")
        sorted_reasons = sorted(
            stats["rejection_reasons"].items(), key=lambda x: x[1], reverse=True
        )
        for reason, count in sorted_reasons[:10]:
            print(f"  {reason}: {count}")

        if stats["passed_jobs"]:
            print(f"\nJobs That Passed ({len(stats['passed_jobs'])}):")
            for job in stats["passed_jobs"]:
                print(f"  - {job['title']} at {job['company']} ({job['strikes']} strikes)")

        print("\n" + "=" * 80)
        print("DATABASE CLEANUP COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    cleaner = DatabaseCleaner()
    cleaner.run()
