#!/usr/bin/env python3
# type: ignore
"""
Explore Firestore collections to understand data structure.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from job_finder.storage.firestore_client import FirestoreClient  # noqa: E402


def explore_collections(database_name: str):
    """Explore all collections in a Firestore database."""
    print(f"\n{'='*70}")
    print(f"Exploring Firestore Database: {database_name}")
    print(f"{'='*70}\n")

    db = FirestoreClient.get_client(database_name)

    # Get all collections
    collections = db.collections()

    for collection in collections:
        collection_name = collection.id
        print(f"\n📂 Collection: {collection_name}")
        print(f"   {'─'*60}")

        # Get document count and sample
        docs = list(collection.limit(5).stream())
        total_count = len(list(collection.stream()))

        print(f"   Total documents: {total_count}")
        print("   Sample documents (first 5):\n")

        for i, doc in enumerate(docs, 1):
            data = doc.to_dict()
            print(f"   [{i}] ID: {doc.id}")

            # Show key fields
            if data:
                # Show first few keys
                keys = list(data.keys())[:10]
                for key in keys:
                    value = data[key]
                    # Truncate long values
                    if isinstance(value, str) and len(value) > 80:
                        value = value[:77] + "..."
                    elif isinstance(value, dict):
                        value = f"{{...}} ({len(value)} keys)"
                    elif isinstance(value, list):
                        value = f"[...] ({len(value)} items)"
                    print(f"       {key}: {value}")

                if len(data.keys()) > 10:
                    print(f"       ... and {len(data.keys()) - 10} more fields")
            print()

    print(f"\n{'='*70}\n")


def main():
    """Main function."""
    print("\n🔍 Firestore Data Explorer")
    print("=" * 70)

    # Explore portfolio database
    print("\n1. job-finder-FE Database (used by job-finder-FE app)")
    explore_collections("portfolio")

    # Explore portfolio-staging database
    print("\n2. job-finder-FE-Staging Database (used by Job Finder)")
    explore_collections("portfolio-staging")


if __name__ == "__main__":
    main()
