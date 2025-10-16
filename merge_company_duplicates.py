#!/usr/bin/env python3
# type: ignore
"""Merge duplicate company records in Firestore."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from job_finder.storage.firestore_client import FirestoreClient  # noqa: E402


def main():
    """Merge duplicate company records."""
    print("\n" + "=" * 70)
    print("Merging Duplicate Company Records")
    print("=" * 70 + "\n")

    staging_db = FirestoreClient.get_client("portfolio-staging")
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

    # Find and merge duplicates
    duplicates_found = 0
    for name_lower, records in companies_by_name.items():
        if len(records) <= 1:
            continue

        duplicates_found += 1
        print(f"\nProcessing duplicate: {name_lower} ({len(records)} records)")

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

        print(f"  Base record: {keep_id}")

        # Merge in missing fields from other records
        merged_fields = []
        for i, (doc_id, data) in enumerate(records):
            if i == operational_idx:
                continue

            print(f"  Merging from: {doc_id}")
            for key, value in data.items():
                if value and (key not in keep_data or not keep_data[key]):
                    keep_data[key] = value
                    merged_fields.append(key)

        if merged_fields:
            print(f"  Merged fields: {', '.join(set(merged_fields))}")

        # Update the kept record with merged data
        companies_collection.document(keep_id).update(keep_data)
        print(f"  ✓ Updated record: {keep_id}")

        # Delete other records
        delete_ids = [doc_id for i, (doc_id, _) in enumerate(records) if i != operational_idx]
        for doc_id in delete_ids:
            companies_collection.document(doc_id).delete()
            print(f"  ✓ Deleted duplicate: {doc_id}")

    if duplicates_found == 0:
        print("✓ No duplicate company records found")
    else:
        print(f"\n{'=' * 70}")
        print(f"Merged {duplicates_found} duplicate company records")
        print("=" * 70)


if __name__ == "__main__":
    main()
