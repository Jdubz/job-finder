#!/usr/bin/env python3
"""Debug script to inspect Firestore data structure."""
import json

from dotenv import load_dotenv

from job_finder.profile import FirestoreProfileLoader

load_dotenv()

print("=" * 70)
print("FIRESTORE DATA INSPECTION")
print("=" * 70)

loader = FirestoreProfileLoader(database_name="portfolio")

# Load raw data
print("\n📦 Loading raw Firestore data...")
experiences = loader._load_experiences(user_id=None)
blurbs = loader._load_experience_blurbs(user_id=None)

print(f"\n✓ Loaded {len(experiences)} experiences")
print(f"✓ Loaded {len(blurbs)} blurbs")

# Inspect first experience entry
if experiences:
    print("\n" + "=" * 70)
    print("SAMPLE EXPERIENCE ENTRY")
    print("=" * 70)
    exp = experiences[0]
    print(f"\nCompany: {exp.company}")
    print(f"Title: {exp.title}")
    print(f"Technologies: {exp.technologies}")
    print(f"Responsibilities: {exp.responsibilities[:2] if exp.responsibilities else []}")
    print(f"\nFull Experience Object:")
    print(json.dumps(exp.model_dump(), indent=2, default=str))

# Inspect first few blurbs
if blurbs:
    print("\n" + "=" * 70)
    print("SAMPLE BLURBS (first 3)")
    print("=" * 70)
    for i, blurb in enumerate(blurbs[:3]):
        print(f"\nBlurb {i+1}:")
        print(json.dumps(blurb, indent=2, default=str))

# Check extracted skills
print("\n" + "=" * 70)
print("EXTRACTED SKILLS")
print("=" * 70)
skills = loader._extract_skills(experiences, blurbs)
print(f"\nTotal skills extracted: {len(skills)}")
for skill in skills:
    print(f"  - {skill.name} (category: {skill.category})")
