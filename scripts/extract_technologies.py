#!/usr/bin/env python3
"""
Extract all technologies mentioned in job descriptions.

Scans all job-matches and extracts unique technology mentions
to help build the technology ranking configuration.
"""

import logging
import re
from collections import Counter
from typing import Set, List

from job_finder.storage.firestore_client import FirestoreClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_NAME = "portfolio-staging"
CREDENTIALS_PATH = ".firebase/static-sites-257923-firebase-adminsdk.json"

# Common technology patterns to extract
TECH_PATTERNS = [
    # Languages
    r'\b(Python|JavaScript|TypeScript|Java|C\+\+|C#|Ruby|Go|Rust|PHP|Perl|Swift|Kotlin|Scala|Elixir|Clojure)\b',
    # Frameworks - Frontend
    r'\b(React|Angular|Vue\.js|Svelte|Next\.js|Nuxt\.js|Ember\.js|Backbone\.js)\b',
    # Frameworks - Backend
    r'\b(Node\.js|Express|Django|Flask|FastAPI|Spring|Spring Boot|Rails|Ruby on Rails|Laravel|\.NET|ASP\.NET)\b',
    # Databases
    r'\b(PostgreSQL|MySQL|MongoDB|Redis|Cassandra|DynamoDB|Elasticsearch|Neo4j|CouchDB|MariaDB)\b',
    # Cloud Platforms
    r'\b(AWS|Azure|GCP|Google Cloud|Heroku|DigitalOcean|Linode)\b',
    # Cloud Services
    r'\b(EC2|S3|Lambda|CloudFront|RDS|DynamoDB|ECS|EKS|Cloud Functions|Cloud Run|App Engine)\b',
    # DevOps/Infrastructure
    r'\b(Docker|Kubernetes|Terraform|Ansible|Jenkins|CircleCI|GitHub Actions|GitLab CI|Travis CI)\b',
    # Message Queues
    r'\b(Kafka|RabbitMQ|SQS|Pub/Sub|NATS|ActiveMQ)\b',
    # Monitoring
    r'\b(Prometheus|Grafana|Datadog|New Relic|Sentry|PagerDuty|CloudWatch)\b',
    # Testing
    r'\b(Jest|Mocha|Pytest|JUnit|Selenium|Cypress|Playwright|TestCafe)\b',
    # APIs
    r'\b(REST|GraphQL|gRPC|SOAP|WebSockets)\b',
    # Other
    r'\b(Git|Linux|Bash|SQL|NoSQL|Microservices|Serverless|CI/CD)\b',
]


class TechnologyExtractor:
    """Extract technologies from job descriptions."""

    def __init__(self):
        """Initialize with Firestore client."""
        self.db = FirestoreClient.get_client(DATABASE_NAME, CREDENTIALS_PATH)
        self.tech_pattern = re.compile('|'.join(TECH_PATTERNS), re.IGNORECASE)

    def extract_from_text(self, text: str) -> Set[str]:
        """
        Extract technology mentions from text.

        Args:
            text: Text to extract from (title + description)

        Returns:
            Set of unique technology names found
        """
        if not text:
            return set()

        # Find all matches
        matches = self.tech_pattern.findall(text)

        # Flatten tuples (regex groups) and clean up
        technologies = set()
        for match in matches:
            if isinstance(match, tuple):
                # Take first non-empty group
                tech = next((m for m in match if m), None)
                if tech:
                    technologies.add(tech)
            else:
                technologies.add(match)

        return technologies

    def scan_job_matches(self) -> Counter:
        """
        Scan all job matches and count technology mentions.

        Returns:
            Counter of technology mentions
        """
        logger.info("Scanning job-matches for technologies...")

        docs = self.db.collection("job-matches").stream()

        tech_counter = Counter()
        job_count = 0

        for doc in docs:
            data = doc.to_dict()
            job_count += 1

            # Combine title and description
            title = data.get("job_title", "")
            description = data.get("job_description", "")
            text = f"{title} {description}"

            # Extract technologies
            technologies = self.extract_from_text(text)

            # Update counter
            for tech in technologies:
                tech_counter[tech] += 1

            if job_count % 10 == 0:
                logger.info(f"Processed {job_count} jobs, found {len(tech_counter)} unique technologies")

        logger.info(f"Scanned {job_count} total jobs")
        logger.info(f"Found {len(tech_counter)} unique technologies")

        return tech_counter

    def generate_config_template(self, tech_counter: Counter) -> dict:
        """
        Generate technology ranking configuration template.

        Args:
            tech_counter: Counter of technology mentions

        Returns:
            Configuration dictionary template
        """
        # Sort by frequency
        sorted_tech = tech_counter.most_common()

        # Categorize by known good/bad tech
        known_required = {"Python", "TypeScript", "JavaScript", "React", "Angular", "Node.js", "GCP", "Kubernetes", "Docker"}
        known_bad = {"Java", "PHP", "Ruby", "Rails", "Ruby on Rails", "WordPress"}

        config = {
            "technologies": {},
            "stats": {
                "total_unique": len(tech_counter),
                "most_common_10": [{"name": tech, "count": count} for tech, count in sorted_tech[:10]]
            }
        }

        for tech, count in sorted_tech:
            # Determine default rank
            if tech in known_required:
                rank = "required"
            elif tech in known_bad:
                rank = "strike"
            else:
                rank = "ok"  # Default to neutral

            config["technologies"][tech] = {
                "rank": rank,  # "required", "ok", "strike", "fail"
                "mentions": count,
                "points": 2 if rank == "strike" else 0,  # Strike points
            }

        return config

    def run(self) -> None:
        """Run technology extraction and generate config."""
        logger.info("=" * 80)
        logger.info("TECHNOLOGY EXTRACTION")
        logger.info("=" * 80)

        # Scan jobs
        tech_counter = self.scan_job_matches()

        # Generate config
        config = self.generate_config_template(tech_counter)

        # Print results
        print("\n" + "=" * 80)
        print("TECHNOLOGY RANKING CONFIGURATION TEMPLATE")
        print("=" * 80)
        print("\nMost Common Technologies:")
        for item in config["stats"]["most_common_10"]:
            print(f"  {item['name']}: {item['count']} mentions")

        print(f"\nTotal unique technologies: {config['stats']['total_unique']}")

        print("\n" + "=" * 80)
        print("CONFIGURATION (for Firestore job-finder-config/technology-ranks)")
        print("=" * 80)
        print("\nRank Legend:")
        print("  required: Must have at least one (0 points)")
        print("  ok: No effect (0 points)")
        print("  strike: Minor negative (2 points)")
        print("  fail: Immediate rejection (hard reject)")

        print("\nTechnologies by Rank:")

        # Group by rank
        by_rank = {
            "required": [],
            "ok": [],
            "strike": [],
            "fail": []
        }

        for tech, data in sorted(config["technologies"].items(), key=lambda x: x[1]["mentions"], reverse=True):
            by_rank[data["rank"]].append(f"{tech} ({data['mentions']})")

        for rank in ["required", "ok", "strike", "fail"]:
            if by_rank[rank]:
                print(f"\n{rank.upper()}:")
                for tech in by_rank[rank][:20]:  # Show top 20 per category
                    print(f"  - {tech}")

        print("\n" + "=" * 80)
        print("Next Steps:")
        print("1. Review the technology list above")
        print("2. Manually adjust ranks as needed")
        print("3. Upload to Firestore: job-finder-config/technology-ranks")
        print("4. Technologies not in config default to 'ok' (neutral)")
        print("=" * 80)


if __name__ == "__main__":
    extractor = TechnologyExtractor()
    extractor.run()
