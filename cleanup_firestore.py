#!/usr/bin/env python3
# type: ignore
"""
Firestore cleanup script.

This script:
1. Backs up legacy data to ../legacy-data/
2. Removes duplicate/obsolete collections
3. Cleans up messy records
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from job_finder.storage.firestore_client import FirestoreClient  # noqa: E402


def backup_collection(db, collection_name: str, backup_dir: Path, db_name: str):
    """Back up a collection to JSON file."""
    print(f"  Backing up {collection_name}...")

    collection = db.collection(collection_name)
    docs = list(collection.stream())

    backup_data = []
    for doc in docs:
        data = doc.to_dict()
        data["_firestore_id"] = doc.id
        backup_data.append(data)

    # Save to file
    backup_file = backup_dir / f"{db_name}_{collection_name}.json"
    with open(backup_file, "w") as f:
        json.dump(backup_data, f, indent=2, default=str)

    print(f"    ✓ Backed up {len(backup_data)} documents to {backup_file}")
    return len(backup_data)


def delete_collection(db, collection_name: str, batch_size: int = 100):
    """Delete all documents in a collection."""
    print(f"  Deleting {collection_name}...")

    collection = db.collection(collection_name)
    deleted_count = 0

    while True:
        docs = list(collection.limit(batch_size).stream())
        if not docs:
            break

        batch = db.batch()
        for doc in docs:
            batch.delete(doc.reference)
            deleted_count += 1

        batch.commit()

    print(f"    ✓ Deleted {deleted_count} documents from {collection_name}")
    return deleted_count


def main():
    """Main cleanup function."""
    print("\n" + "=" * 70)
    print("Firestore Data Cleanup")
    print("=" * 70 + "\n")

    # Create backup directory
    backup_dir = Path(__file__).parent.parent / "legacy-data"
    backup_dir.mkdir(exist_ok=True)
    print(f"Backup directory: {backup_dir}\n")

    # Get staging database client
    staging_db = FirestoreClient.get_client("portfolio-staging")

    # ==========================================================================
    # PHASE 1: Backup collections that will be removed
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: Backing up collections to be removed")
    print("=" * 70 + "\n")

    # Collections to remove from portfolio-staging (duplicates from portfolio)
    duplicate_collections = [
        "contact-submissions",
        "experience-blurbs",
        "experience-entries",
    ]

    for collection_name in duplicate_collections:
        backup_collection(staging_db, collection_name, backup_dir, "portfolio-staging")

    # ==========================================================================
    # PHASE 2: Remove duplicate collections from portfolio-staging
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: Removing duplicate collections from portfolio-staging")
    print("=" * 70 + "\n")
    print("These collections are duplicates from the portfolio database.")
    print("They should only exist in the portfolio database.\n")

    response = input("Proceed with deletion? (yes/no): ")
    if response.lower() != "yes":
        print("Aborted. No collections deleted.")
        return

    for collection_name in duplicate_collections:
        delete_collection(staging_db, collection_name)

    # ==========================================================================
    # PHASE 3: Clean up duplicate company records
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PHASE 3: Analyzing duplicate company records")
    print("=" * 70 + "\n")

    companies_collection = staging_db.collection("companies")
    companies = list(companies_collection.stream())

    # Group by name_lower
    companies_by_name = {}
    for doc in companies:
        data = doc.to_dict()
        name_lower = data.get("name_lower", "").lower()
        if name_lower not in companies_by_name:
            companies_by_name[name_lower] = []
        companies_by_name[name_lower].append((doc.id, data))

    # Find duplicates
    duplicates_found = 0
    for name_lower, records in companies_by_name.items():
        if len(records) > 1:
            duplicates_found += 1
            print(f"\n  Duplicate company found: {name_lower}")
            print(f"    Total records: {len(records)}")

            # Show details of each record
            for i, (doc_id, data) in enumerate(records, 1):
                print(f"\n    Record {i} (ID: {doc_id}):")
                for key in [
                    "about",
                    "industry",
                    "tier",
                    "priorityScore",
                    "company_size_category",
                ]:
                    value = data.get(key, "")
                    if value:
                        truncated = str(value)[:80] + "..." if len(str(value)) > 80 else str(value)
                        print(f"      {key}: {truncated}")

            # Merge strategy: Combine data from all records
            # Keep the record with most scoring data (tier/priorityScore)
            # Merge in additional fields from other records

            # Find record with tier/priority score (operational data)
            operational_idx = None
            for i, (doc_id, data) in enumerate(records):
                if data.get("tier") or data.get("priorityScore"):
                    operational_idx = i
                    break

            if operational_idx is None:
                operational_idx = 0  # Default to first

            keep_id = records[operational_idx][0]
            keep_data = records[operational_idx][1].copy()

            # Merge in missing fields from other records
            for i, (doc_id, data) in enumerate(records):
                if i == operational_idx:
                    continue

                for key, value in data.items():
                    if key not in keep_data or not keep_data[key]:
                        keep_data[key] = value

            # Update the kept record with merged data
            companies_collection.document(keep_id).update(keep_data)

            # Delete other records
            delete_ids = [doc_id for i, (doc_id, _) in enumerate(records) if i != operational_idx]

            print(f"\n    → Merged data into record {operational_idx + 1} (ID: {keep_id})")
            print(f"    → Deleting {len(delete_ids)} duplicate(s)")

            for doc_id in delete_ids:
                companies_collection.document(doc_id).delete()
                print(f"      ✓ Deleted duplicate: {doc_id}")

    if duplicates_found == 0:
        print("  ✓ No duplicate company records found")

    # ==========================================================================
    # PHASE 4: Summary
    # ==========================================================================
    print("\n" + "=" * 70)
    print("Cleanup Complete!")
    print("=" * 70 + "\n")

    print("Summary:")
    print(f"  - Backed up {len(duplicate_collections)} collections to {backup_dir}")
    print(f"  - Removed {len(duplicate_collections)} duplicate collections from portfolio-staging")
    print(f"  - Processed {duplicates_found} duplicate company records")
    print("\nNext steps:")
    print("  1. Review backup files in ../legacy-data/")
    print("  2. Manually review and clean up messy job-matches records")
    print("  3. Consider consolidating job-listings between databases")


if __name__ == "__main__":
    main()
