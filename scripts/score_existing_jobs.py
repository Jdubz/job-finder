#!/usr/bin/env python3
"""
Score existing job matches with new strike-based filter system.

Analyzes all jobs in job-matches to see how they would score
under the new filtering system, without modifying them.

This helps tune strike thresholds before actual deployment.
"""

import json
import logging
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any

from job_finder.filters.strike_filter_engine import StrikeFilterEngine
from job_finder.storage.firestore_client import FirestoreClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_NAME = "portfolio-staging"
CREDENTIALS_PATH = ".firebase/static-sites-257923-firebase-adminsdk.json"
OUTPUT_DIR = Path("data/analysis")


# Default configurations (will be loaded from Firestore in production)
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
        "strikeDays": 1,  # > 1 day = strike
        "rejectDays": 7,  # > 7 days = hard reject
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


class JobScorer:
    """Score existing jobs with strike-based filter."""

    def __init__(self):
        """Initialize with Firestore client."""
        self.db = FirestoreClient.get_client(DATABASE_NAME, CREDENTIALS_PATH)
        self.filter_engine = StrikeFilterEngine(DEFAULT_FILTER_CONFIG, DEFAULT_TECH_RANKS)

    def score_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Score all job matches.

        Returns:
            List of scored jobs with filter results
        """
        logger.info("Scoring all job-matches...")

        docs = self.db.collection("job-matches").stream()

        scored_jobs = []
        job_count = 0

        for doc in docs:
            data = doc.to_dict()
            job_count += 1

            # Prepare job data for filtering (use actual field names from job-matches)
            job_data = {
                "title": data.get("title", ""),
                "company": data.get("company", ""),
                "description": data.get("description", ""),
                "location": data.get("location", ""),
                "salary": data.get("salary", ""),
                "posted_date": data.get("postedDate"),  # ISO format string
                "url": data.get("url", ""),
            }

            # Run filter
            result = self.filter_engine.evaluate_job(job_data)

            # Store result
            scored_jobs.append(
                {
                    "job_id": doc.id,
                    "title": job_data["title"],
                    "company": job_data["company"],
                    "url": job_data["url"],
                    "passed": result.passed,
                    "total_strikes": result.total_strikes,
                    "strike_threshold": result.strike_threshold,
                    "hard_rejections": [
                        r.to_dict() for r in result.rejections if r.severity == "hard_reject"
                    ],
                    "strikes": [r.to_dict() for r in result.rejections if r.severity == "strike"],
                    "rejection_summary": result.get_rejection_summary(),
                }
            )

            if job_count % 10 == 0:
                logger.info(f"Scored {job_count} jobs...")

        logger.info(f"Scored {job_count} total jobs")
        return scored_jobs

    def analyze_results(self, scored_jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze scoring results.

        Args:
            scored_jobs: List of scored jobs

        Returns:
            Analysis dictionary
        """
        total = len(scored_jobs)
        passed = sum(1 for j in scored_jobs if j["passed"])
        failed = total - passed

        # Count by strike count
        strike_distribution = Counter()
        for job in scored_jobs:
            strike_distribution[job["total_strikes"]] += 1

        # Count by rejection type
        hard_reject_reasons = Counter()
        strike_reasons = Counter()

        for job in scored_jobs:
            for rejection in job["hard_rejections"]:
                hard_reject_reasons[rejection["reason"]] += 1

            for strike in job["strikes"]:
                strike_reasons[strike["reason"]] += 1

        # Find borderline jobs (3-4 strikes)
        borderline = [j for j in scored_jobs if 3 <= j["total_strikes"] <= 4]

        # Find excellent jobs (0-1 strikes)
        excellent = [j for j in scored_jobs if j["total_strikes"] <= 1 and j["passed"]]

        return {
            "total_jobs": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%",
            "strike_distribution": dict(sorted(strike_distribution.items())),
            "hard_reject_reasons": dict(hard_reject_reasons.most_common(10)),
            "strike_reasons": dict(strike_reasons.most_common(10)),
            "borderline_count": len(borderline),
            "excellent_count": len(excellent),
            "borderline_examples": borderline[:5],
            "excellent_examples": excellent[:5],
        }

    def run(self):
        """Run full scoring and analysis."""
        logger.info("=" * 80)
        logger.info("JOB SCORING ANALYSIS")
        logger.info("=" * 80)
        logger.info(f"Strike Threshold: {DEFAULT_FILTER_CONFIG['strikeThreshold']}")
        logger.info("=" * 80)

        # Score jobs
        scored_jobs = self.score_all_jobs()

        # Analyze
        analysis = self.analyze_results(scored_jobs)

        # Save results
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_file = OUTPUT_DIR / "job_scoring_results.json"

        with open(output_file, "w") as f:
            json.dump({"analysis": analysis, "scored_jobs": scored_jobs}, f, indent=2)

        logger.info(f"Saved results to: {output_file}")

        # Print summary
        print("\n" + "=" * 80)
        print("SCORING SUMMARY")
        print("=" * 80)
        print(f"\nTotal Jobs: {analysis['total_jobs']}")
        print(f"Passed: {analysis['passed']} ({analysis['pass_rate']})")
        print(f"Failed: {analysis['failed']}")
        print(f"Excellent (0-1 strikes): {analysis['excellent_count']}")
        print(f"Borderline (3-4 strikes): {analysis['borderline_count']}")

        print("\nStrike Distribution:")
        for strikes, count in analysis["strike_distribution"].items():
            print(f"  {strikes} strikes: {count} jobs")

        print("\nTop Hard Rejection Reasons:")
        for reason, count in list(analysis["hard_reject_reasons"].items())[:5]:
            print(f"  {reason}: {count}")

        print("\nTop Strike Reasons:")
        for reason, count in list(analysis["strike_reasons"].items())[:5]:
            print(f"  {reason}: {count}")

        if analysis["borderline_examples"]:
            print("\nBorderline Job Examples (would pass with threshold=5, fail with threshold=3):")
            for job in analysis["borderline_examples"]:
                print(f"  - {job['title']} at {job['company']} ({job['total_strikes']} strikes)")
                for strike in job["strikes"][:2]:
                    print(f"    • {strike['reason']}")

        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)

        pass_rate = float(analysis["pass_rate"].rstrip("%"))
        if pass_rate < 30:
            print("⚠️  Very strict filtering (< 30% pass rate)")
            print("   Consider raising strike threshold or adjusting strike points")
        elif pass_rate < 50:
            print("✅ Moderate filtering (30-50% pass rate)")
            print("   Good balance for high-quality candidates")
        else:
            print("⚠️  Lenient filtering (> 50% pass rate)")
            print("   Consider lowering strike threshold for higher quality")

        print("\nNext Steps:")
        print("1. Review borderline job examples")
        print("2. Adjust strike points and threshold as needed")
        print("3. Run tech extraction to add more technologies")
        print("4. Deploy updated filter config to Firestore")
        print("=" * 80)


if __name__ == "__main__":
    scorer = JobScorer()
    scorer.run()
