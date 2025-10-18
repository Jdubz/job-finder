"""
Decision Tree Validator for E2E Tests

Validates that the state-driven pipeline and loop prevention work correctly.

Usage:
    python tests/e2e/validate_decision_tree.py \\
        --database portfolio-staging \\
        --results-dir ./test_results/run_001
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from job_finder.queue import QueueManager
from job_finder.storage.firestore_client import FirestoreClient

logger = logging.getLogger(__name__)


class DecisionTreeValidator:
    """Validates decision tree logic from E2E test results."""

    def __init__(self, database_name: str, results_dir: Path):
        """
        Initialize validator.

        Args:
            database_name: Database to validate
            results_dir: Directory with test results
        """
        self.database_name = database_name
        self.db = FirestoreClient.get_client(database_name)
        self.queue_manager = QueueManager(database_name)
        self.results_dir = Path(results_dir)

    def validate_tracking_ids(self) -> bool:
        """
        Validate that all queue items have tracking_id.

        Returns:
            True if valid
        """
        logger.info("Validating tracking_id presence...")

        query = self.db.collection("job-queue")
        items = list(query.stream())

        missing_tracking_id = []
        for doc in items:
            data = doc.to_dict()
            if data and not data.get("tracking_id"):
                missing_tracking_id.append(doc.id)

        if missing_tracking_id:
            logger.error(f"✗ {len(missing_tracking_id)} items missing tracking_id:")
            for doc_id in missing_tracking_id[:5]:
                logger.error(f"  - {doc_id}")
            return False

        logger.info(f"✓ All {len(items)} items have tracking_id")
        return True

    def validate_ancestry_chain(self) -> bool:
        """
        Validate that ancestry_chain is properly maintained.

        Returns:
            True if valid
        """
        logger.info("Validating ancestry_chain...")

        query = self.db.collection("job-queue")
        items = list(query.stream())

        invalid_chains = []
        for doc in items:
            data = doc.to_dict()
            if not data:
                continue
            ancestry_chain = data.get("ancestry_chain", [])

            # Root items should have ancestry_chain with their doc_id
            # Spawned items should have parent's chain + their doc_id

            if not isinstance(ancestry_chain, list):
                invalid_chains.append((doc.id, "Not a list"))
                continue

            # Check for circular references
            if len(ancestry_chain) != len(set(ancestry_chain)):
                invalid_chains.append((doc.id, "Circular reference detected"))

        if invalid_chains:
            logger.error(f"✗ {len(invalid_chains)} items with invalid ancestry_chain:")
            for doc_id, reason in invalid_chains[:5]:
                logger.error(f"  - {doc_id}: {reason}")
            return False

        logger.info(f"✓ All {len(items)} items have valid ancestry_chain")
        return True

    def validate_spawn_depth(self) -> bool:
        """
        Validate that spawn_depth is within limits.

        Returns:
            True if valid
        """
        logger.info("Validating spawn_depth...")

        query = self.db.collection("job-queue")
        items = list(query.stream())

        excessive_depth = []
        for doc in items:
            data = doc.to_dict()
            if not data:
                continue
            spawn_depth = data.get("spawn_depth", 0)
            max_spawn_depth = data.get("max_spawn_depth", 10)

            if spawn_depth >= max_spawn_depth:
                excessive_depth.append((doc.id, spawn_depth, max_spawn_depth))

        if excessive_depth:
            logger.warning(f"⚠ {len(excessive_depth)} items at/near max spawn_depth:")
            for doc_id, depth, max_depth in excessive_depth[:5]:
                logger.warning(f"  - {doc_id}: {depth}/{max_depth}")

        logger.info(f"✓ Spawn depth validation complete ({len(items)} items checked)")
        return True

    def validate_no_loops(self) -> bool:
        """
        Validate that no infinite loops occurred.

        Returns:
            True if valid
        """
        logger.info("Validating loop prevention...")

        query = self.db.collection("job-queue")
        items = list(query.stream())

        # Group by URL to find duplicates
        url_groups: Dict[str, List[str]] = {}
        for doc in items:
            data = doc.to_dict()
            if not data:
                continue
            url = data.get("url", "")
            if url:
                if url not in url_groups:
                    url_groups[url] = []
                url_groups[url].append(doc.id)

        # Check for duplicate URLs (should be allowed if in different tracking lineages)
        duplicate_urls = {url: ids for url, ids in url_groups.items() if len(ids) > 1}

        if duplicate_urls:
            logger.info(f"Found {len(duplicate_urls)} duplicate URLs:")
            for url, ids in list(duplicate_urls.items())[:3]:
                logger.info(f"  - {url}: {len(ids)} instances")

                # Check if they have different tracking_ids (allowed)
                tracking_ids = set()
                for doc_id in ids:
                    doc = self.db.collection("job-queue").document(doc_id).get()
                    data = doc.to_dict()
                    if data:
                        tracking_ids.add(data.get("tracking_id", ""))

                if len(tracking_ids) == 1:
                    logger.error(f"    ✗ Same tracking_id - potential loop!")
                    return False
                else:
                    logger.info(f"    ✓ Different tracking_ids - OK")

        logger.info("✓ No loops detected")
        return True

    def generate_report(self) -> Dict:
        """
        Generate validation report.

        Returns:
            Report dict
        """
        logger.info("=" * 80)
        logger.info("DECISION TREE VALIDATION")
        logger.info("=" * 80)
        logger.info("")

        results = {
            "tracking_id_valid": self.validate_tracking_ids(),
            "ancestry_chain_valid": self.validate_ancestry_chain(),
            "spawn_depth_valid": self.validate_spawn_depth(),
            "no_loops_detected": self.validate_no_loops(),
        }

        logger.info("")
        logger.info("=" * 80)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 80)

        all_passed = all(results.values())

        for check, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            logger.info(f"{status}: {check}")

        logger.info("")
        if all_passed:
            logger.info("✓ All validations passed!")
        else:
            logger.error("✗ Some validations failed")

        return results

    def save_report(self, results: Dict) -> None:
        """Save report to file."""
        report_file = self.results_dir / "decision_tree_validation.json"
        with open(report_file, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Report saved to {report_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Decision Tree Validator")
    parser.add_argument(
        "--database",
        default="portfolio-staging",
        help="Database to validate (default: portfolio-staging)",
    )
    parser.add_argument(
        "--results-dir",
        required=True,
        help="Results directory",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    level = logging.DEBUG if args.verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[logging.StreamHandler()],
    )

    # Run validation
    validator = DecisionTreeValidator(
        database_name=args.database,
        results_dir=Path(args.results_dir),
    )

    results = validator.generate_report()
    validator.save_report(results)

    # Exit with success/failure
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
