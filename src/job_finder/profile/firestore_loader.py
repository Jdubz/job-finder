"""Load profile data from Firestore database."""
import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore as gcloud_firestore

from job_finder.profile.schema import Profile, Experience, Education, Skill

logger = logging.getLogger(__name__)


class FirestoreProfileLoader:
    """Loads profile data from Firestore database."""

    def __init__(self, credentials_path: Optional[str] = None, database_name: str = "portfolio"):
        """
        Initialize Firestore connection.

        Args:
            credentials_path: Path to Firebase service account JSON.
                            Defaults to GOOGLE_APPLICATION_CREDENTIALS env var.
            database_name: Firestore database name (default: "portfolio").
        """
        self.database_name = database_name
        self.db: Optional[gcloud_firestore.Client] = None

        # Get credentials path
        creds_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not creds_path:
            raise ValueError(
                "Firebase credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS "
                "environment variable or pass credentials_path parameter."
            )

        if not Path(creds_path).exists():
            raise FileNotFoundError(f"Credentials file not found: {creds_path}")

        # Initialize Firebase Admin
        try:
            # Load credentials for project ID (needed regardless of initialization status)
            cred = credentials.Certificate(creds_path)

            # Check if already initialized
            try:
                firebase_admin.get_app()
                logger.info("Using existing Firebase app")
            except ValueError:
                # Initialize new app
                firebase_admin.initialize_app(cred)
                logger.info("Initialized new Firebase app")

            # Get Firestore client for the specified database
            # Use google-cloud-firestore Client directly to support named databases
            project_id = cred.project_id

            if database_name == "(default)":
                self.db = gcloud_firestore.Client(project=project_id)
            else:
                # Connect to named database
                self.db = gcloud_firestore.Client(project=project_id, database=database_name)

            logger.info(f"Connected to Firestore database: {database_name} in project {project_id}")

        except Exception as e:
            raise RuntimeError(f"Failed to initialize Firestore: {str(e)}") from e

    def load_profile(
        self,
        user_id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None
    ) -> Profile:
        """
        Load profile from Firestore.

        Args:
            user_id: User ID to load profile for.
            name: User name to use in profile.
            email: User email to use in profile.

        Returns:
            Profile instance populated with Firestore data.
        """
        if not self.db:
            raise RuntimeError("Firestore not initialized")

        logger.info(f"Loading profile from Firestore (user_id: {user_id})")

        # Load experience entries
        experiences = self._load_experiences(user_id)
        logger.info(f"Loaded {len(experiences)} experience entries")

        # Load experience blurbs (skills/highlights)
        blurbs = self._load_experience_blurbs(user_id)
        logger.info(f"Loaded {len(blurbs)} experience blurbs")

        # Extract skills from experiences and blurbs
        skills = self._extract_skills(experiences, blurbs)
        logger.info(f"Extracted {len(skills)} unique skills")

        # Build profile
        profile = Profile(
            name=name or "User",
            email=email,
            summary=self._generate_summary(experiences, blurbs),
            years_of_experience=self._calculate_years_experience(experiences),
            skills=skills,
            experience=experiences,
            education=[],  # TODO: Add education collection if available
            projects=[],  # TODO: Add projects collection if available
        )

        logger.info(f"Successfully loaded profile with {len(experiences)} experiences and {len(skills)} skills")
        return profile

    def _load_experiences(self, user_id: Optional[str] = None) -> List[Experience]:
        """Load experience entries from Firestore."""
        experiences = []

        try:
            # Query experience-entries collection
            query = self.db.collection("experience-entries")
            if user_id:
                query = query.where("userId", "==", user_id)

            # Order by start date descending (most recent first)
            query = query.order_by("startDate", direction=gcloud_firestore.Query.DESCENDING)

            docs = query.stream()

            for doc in docs:
                data = doc.to_dict()

                # Firestore schema:
                # - title = Company name
                # - role = Job title
                # - body = Description (may contain "Stack: ..." section)
                company = data.get("title", "")
                title = data.get("role", "")
                body = data.get("body", "")

                # Parse technologies from body (look for "Stack:" section)
                technologies = self._parse_technologies_from_body(body)

                # Map Firestore data to Experience model
                experience = Experience(
                    company=company,
                    title=title,
                    start_date=data.get("startDate", ""),
                    end_date=data.get("endDate"),
                    location=data.get("location", ""),
                    description=body,
                    responsibilities=[],  # Not stored separately in Firestore
                    achievements=[],  # Not stored separately in Firestore
                    technologies=technologies,
                    is_current=data.get("endDate") is None or data.get("endDate") == "",
                )
                experiences.append(experience)

        except Exception as e:
            logger.error(f"Error loading experiences: {str(e)}")
            raise

        return experiences

    def _parse_technologies_from_body(self, body: str) -> List[str]:
        """Extract technologies from experience body text.

        Looks for patterns like:
        - "Stack: Docker, React, ..."
        - "Technologies: Python, AWS, ..."
        """
        import re

        technologies = []

        # Look for "Stack:" or "Technologies:" sections
        patterns = [
            r"Stack:\s*([^\n]+)",
            r"Technologies:\s*([^\n]+)",
            r"Tech Stack:\s*([^\n]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                # Extract comma-separated technologies
                tech_string = match.group(1).strip()
                # Split by comma and clean up
                techs = [t.strip() for t in tech_string.split(",")]
                technologies.extend(techs)

        return technologies

    def _load_experience_blurbs(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load experience blurbs from Firestore.

        Note: These are content sections (biography, education, etc.) for the portfolio website,
        not skill data. We keep this for potential summary generation but don't extract skills from it.
        """
        blurbs = []

        try:
            # Query experience-blurbs collection
            query = self.db.collection("experience-blurbs")
            if user_id:
                query = query.where("userId", "==", user_id)

            docs = query.stream()

            for doc in docs:
                data = doc.to_dict()
                blurbs.append(data)

        except Exception as e:
            logger.error(f"Error loading experience blurbs: {str(e)}")
            raise

        return blurbs

    def _extract_skills(
        self, experiences: List[Experience], blurbs: List[Dict[str, Any]]
    ) -> List[Skill]:
        """Extract and deduplicate skills from experiences.

        Note: Blurbs are portfolio content sections, not skill data, so we only
        extract from experience technologies.
        """
        skills_dict: Dict[str, Skill] = {}

        # Extract from experience technologies
        for exp in experiences:
            for tech in exp.technologies:
                if tech and tech not in skills_dict:
                    skills_dict[tech] = Skill(
                        name=tech,
                        category="technology"
                    )

        return list(skills_dict.values())

    def _generate_summary(
        self, experiences: List[Experience], blurbs: List[Dict[str, Any]]
    ) -> str:
        """Generate a professional summary from experience data."""
        if not experiences:
            return ""

        # Get current or most recent role
        current = experiences[0] if experiences else None
        if not current:
            return ""

        summary_parts = []

        # Current role
        if current.is_current:
            summary_parts.append(f"{current.title} at {current.company}")
        else:
            summary_parts.append(f"Experienced {current.title}")

        # Add first responsibility or achievement if available
        if current.responsibilities:
            summary_parts.append(current.responsibilities[0])
        elif current.achievements:
            summary_parts.append(current.achievements[0])

        return ". ".join(summary_parts) + "."

    def _calculate_years_experience(self, experiences: List[Experience]) -> float:
        """Calculate total years of professional experience."""
        # This is a simplified calculation
        # In production, you'd want to parse dates and calculate actual duration
        return float(len(experiences))

    def close(self):
        """Close Firestore connection."""
        # Firebase Admin SDK doesn't require explicit closing
        # But we can delete the app if needed
        try:
            firebase_admin.delete_app(firebase_admin.get_app())
            logger.info("Closed Firebase connection")
        except Exception as e:
            logger.debug(f"Error closing Firebase: {str(e)}")
