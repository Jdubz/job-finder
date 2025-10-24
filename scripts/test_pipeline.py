#!/usr/bin/env python3
"""Test the complete AI job matching pipeline with a real job posting."""
import json

from dotenv import load_dotenv

from job_finder.ai import AIJobMatcher
from job_finder.ai.providers import create_provider
from job_finder.profile import FirestoreProfileLoader

# Load environment variables
load_dotenv()

print("=" * 70)
print("NETFLIX JOB PIPELINE TEST")
print("=" * 70)

# Sample job from Netflix
netflix_job = {
    "title": "Full Stack Software Engineer (L5) - Delivery Engineering",
    "company": "Netflix",
    "company_website": "https://www.netflix.com",
    "company_info": "Netflix is the world's leading streaming entertainment service with over 230 million paid memberships in over 190 countries. Netflix culture emphasizes freedom and responsibility, with core values including judgment, communication, impact, curiosity, innovation, courage, passion, honesty, and selflessness.",
    "location": "USA - Remote (Portland, OR)",
    "url": "https://explore.jobs.netflix.net/careers?pid=790304772545",
    "description": """
Netflix's Delivery Engineering group is responsible for continuous delivery of
software and infrastructure changes across Netflix services. The team works to
increase productivity, minimize toil, and increase the frequency and safety of
software deployments.

Key Responsibilities:
- Improve user experience across Spinnaker and Managed Delivery platforms
- Build platforms for partner teams to create tailored experiences
- Increase deployment safety and ease

Behaviors Expected:
- Mentorship mindset
- Strong communication skills
- Collaborative approach
- Platform engineering experience
- Provide and take feedback
- Comfortable with ambiguity
- Deep sense of project ownership
- Customer empathy

Qualifications:
- Full stack development skills (front-end and back-end)
- Experience with Java/JVM languages and JavaScript (Angular/React)
- Ability to break down complexity and communicate progress
- Comfortable with on-call rotations

Compensation Range: $100,000 - $720,000 annually

Netflix emphasizes a unique culture of collaboration, high-impact work,
and continuous feedback.
    """.strip(),
    # Note: ATS keywords are stored in resumeIntakeData.atsKeywords, not at job level
}

print("\n📋 JOB POSTING")
print("-" * 70)
print(f"Title: {netflix_job['title']}")
print(f"Company: {netflix_job['company']}")
print(f"Company Website: {netflix_job['company_website']}")
print(f"Company Info: {netflix_job['company_info'][:100]}...")
print(f"Location: {netflix_job['location']}")
print(f"URL: {netflix_job['url']}")
print()

# Step 1: Load profile from Firestore
print("🔄 STEP 1: Loading profile from Firestore...")
print("-" * 70)
try:
    loader = FirestoreProfileLoader(database_name="portfolio")
    profile = loader.load_profile(name="Josh Wentworth", email="Contact@joshwentworth.com")
    print(f"✓ Profile loaded: {profile.name}")
    print(f"  - {len(profile.experience)} experience entries")
    print(f"  - {len(profile.skills)} skills")
    print(f"  - {profile.years_of_experience} years of experience")
except Exception as e:
    print(f"✗ Error loading profile: {str(e)}")
    exit(1)

# Step 2: Initialize AI provider
print("\n🤖 STEP 2: Initializing AI provider...")
print("-" * 70)
try:
    provider = create_provider("claude", model="claude-3-haiku-20240307")
    print("✓ Claude provider initialized (claude-3-haiku-20240307)")
except Exception as e:
    print(f"✗ Error initializing AI: {str(e)}")
    exit(1)

# Step 3: Create AI matcher
print("\n🎯 STEP 3: Creating AI job matcher...")
print("-" * 70)
try:
    matcher = AIJobMatcher(
        provider=provider, profile=profile, min_match_score=70, generate_intake=True
    )
    print("✓ AI matcher created")
    print(f"  - Min match score: 70")
    print(f"  - Resume intake generation: enabled")
except Exception as e:
    print(f"✗ Error creating matcher: {str(e)}")
    exit(1)

# Step 4: Analyze the job
print("\n⚡ STEP 4: Analyzing job with AI...")
print("-" * 70)
print("This may take 10-30 seconds...")
try:
    result = matcher.analyze_job(netflix_job)

    if result:
        print("\n✅ JOB ANALYSIS COMPLETE!")
        print("=" * 70)
        print(f"\n🎯 MATCH SCORE: {result.match_score}/100")
        print(f"📊 PRIORITY: {result.application_priority}")

        print(f"\n✓ MATCHED SKILLS ({len(result.matched_skills)}):")
        for skill in result.matched_skills[:10]:
            print(f"  • {skill}")
        if len(result.matched_skills) > 10:
            print(f"  ... and {len(result.matched_skills) - 10} more")

        print(f"\n⚠️  MISSING SKILLS ({len(result.missing_skills)}):")
        for skill in result.missing_skills[:10]:
            print(f"  • {skill}")
        if len(result.missing_skills) > 10:
            print(f"  ... and {len(result.missing_skills) - 10} more")

        print(f"\n💪 KEY STRENGTHS:")
        for strength in result.key_strengths:
            print(f"  • {strength}")

        print(f"\n🤔 POTENTIAL CONCERNS:")
        for concern in result.potential_concerns:
            print(f"  • {concern}")

        print(f"\n📝 EXPERIENCE MATCH:")
        print(f"  {result.experience_match}")

        # Resume intake data
        if result.resume_intake_data:
            intake = result.resume_intake_data
            print(f"\n📄 RESUME INTAKE DATA GENERATED")
            print("-" * 70)

            print(f"\n🎯 Target Summary:")
            print(f"  {intake.get('target_summary', 'N/A')[:200]}...")

            print(f"\n⭐ Top Skills to Emphasize:")
            for skill in intake.get("skills_priority", [])[:8]:
                print(f"  • {skill}")

            print(f"\n📌 Experience Highlights:")
            for exp in intake.get("experience_highlights", [])[:3]:
                print(f"  • {exp.get('company', 'N/A')}: {exp.get('title', 'N/A')}")
                for point in exp.get("points_to_emphasize", [])[:2]:
                    print(f"    - {point}")

            print(f"\n🔑 ATS Keywords:")
            ats_keywords = intake.get("ats_keywords", [])
            print(f"  {', '.join(ats_keywords[:15])}")
            if len(ats_keywords) > 15:
                print(f"  ... and {len(ats_keywords) - 15} more")

            # Note: ATS keywords are stored in resumeIntakeData, not at job level

            # Save full results
            output_file = "data/netflix_analysis.json"
            with open(output_file, "w") as f:
                json.dump(
                    {
                        "job": netflix_job,
                        "analysis": {
                            "match_score": result.match_score,
                            "matched_skills": result.matched_skills,
                            "missing_skills": result.missing_skills,
                            "experience_match": result.experience_match,
                            "key_strengths": result.key_strengths,
                            "potential_concerns": result.potential_concerns,
                            "application_priority": result.application_priority,
                            "customization_recommendations": result.customization_recommendations,
                            "resume_intake_data": result.resume_intake_data,
                        },
                    },
                    f,
                    indent=2,
                )

            print(f"\n💾 Full analysis saved to: {output_file}")

        # Show exported job data structure
        print(f"\n📊 EXPORTED JOB DATA STRUCTURE")
        print("-" * 70)
        print(f"✓ Role: {netflix_job['title']}")
        print(f"✓ Company: {netflix_job['company']}")
        print(f"✓ Company Website: {netflix_job['company_website']}")
        print(f"✓ Company Info: {len(netflix_job['company_info'])} characters")
        print(f"✓ Job URL: {netflix_job['url']}")
        print(f"✓ Job Description: {len(netflix_job['description'])} characters")
        print(f"✓ Keywords for Emphasis: {len(netflix_job['keywords'])} keywords")
        print(f"   • {', '.join(netflix_job['keywords'][:5])}...")

        print("\n" + "=" * 70)
        print("✅ PIPELINE TEST SUCCESSFUL!")
        print("=" * 70)

    else:
        print("\n⚠️  Job did not meet minimum match score threshold")

except Exception as e:
    print(f"\n✗ Error during analysis: {str(e)}")
    import traceback

    traceback.print_exc()
    exit(1)
