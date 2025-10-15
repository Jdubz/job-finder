#!/usr/bin/env python3
"""Debug script to see raw Firestore document structure."""
import json
import os

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials
from google.cloud import firestore as gcloud_firestore

load_dotenv()

# Initialize Firebase
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
cred = credentials.Certificate(creds_path)

try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred)

project_id = cred.project_id
db = gcloud_firestore.Client(project=project_id, database="portfolio")

print("=" * 70)
print("RAW FIRESTORE DOCUMENT STRUCTURE")
print("=" * 70)

# Get first experience entry
print("\n📋 EXPERIENCE-ENTRIES COLLECTION (First Document)")
print("-" * 70)
exp_query = db.collection("experience-entries").limit(1)
for doc in exp_query.stream():
    data = doc.to_dict()
    print(f"\nDocument ID: {doc.id}")
    print(f"\nAll fields in document:")
    for key in sorted(data.keys()):
        print(f"  {key}: {type(data[key]).__name__}")
    print(f"\nFull document:")
    print(json.dumps(data, indent=2, default=str))

# Get first blurb
print("\n\n📝 EXPERIENCE-BLURBS COLLECTION (First Document)")
print("-" * 70)
blurb_query = db.collection("experience-blurbs").limit(1)
for doc in blurb_query.stream():
    data = doc.to_dict()
    print(f"\nDocument ID: {doc.id}")
    print(f"\nAll fields in document:")
    for key in sorted(data.keys()):
        print(f"  {key}: {type(data[key]).__name__}")
    print(f"\nFull document:")
    print(json.dumps(data, indent=2, default=str))

# Check if there are other collections that might have skills
print("\n\n🔍 ALL COLLECTIONS IN DATABASE")
print("-" * 70)
collections = db.collections()
for collection in collections:
    count = len(list(collection.limit(100).stream()))
    print(f"  - {collection.id} ({count} documents)")
