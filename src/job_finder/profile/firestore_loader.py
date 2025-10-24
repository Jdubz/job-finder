"""Load profile data from Firestore database."""

import logging
from typing import Any, Dict, List, Optional

from google.cloud import firestore as gcloud_firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from job_finder.exceptions import InitializationError
from job_finder.profile.schema import Experience, Profile, Skill
from job_finder.storage.firestore_client import FirestoreClient

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
        self.db = FirestoreClient.get_client(database_name, credentials_path)

    def load_profile(
        self, user_id: Optional[str] = None, name: Optional[str] = None, email: Optional[str] = None
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
            raise InitializationError("Firestore not initialized")

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
            phone=None,
            location=None,
            linkedin_url=None,
            github_url=None,
            portfolio_url=None,
            summary=self._generate_summary(experiences, blurbs),
            years_of_experience=self._calculate_years_experience(experiences),
            skills=skills,
            experience=experiences,
            education=[],  # Not currently stored in job-finder-FE Firestore
            projects=[],  # Not currently stored in job-finder-FE Firestore
            preferences=None,
            certifications=[],
            languages=[],
        )

        logger.info(
            f"Successfully loaded profile with {len(experiences)} experiences "
            f"and {len(skills)} skills"
        )
        return profile

    def _load_experiences(self, user_id: Optional[str] = None) -> List[Experience]:
        """Load experience entries from Firestore."""
        experiences = []

        try:
            # Try new schema first (content-items)
            docs = list(self._query_content_items("company", user_id))

            if docs:
                # New schema
                logger.info("Loading from new content-items schema")
                for doc in docs:
                    experience = self._process_content_item_doc(doc)
                    if experience:
                        experiences.append(experience)
            else:
                # Fallback to old schema (experience-entries)
                logger.info("Falling back to old experience-entries schema")
                docs = self._query_experience_docs(user_id)
                for doc in docs:
                    experience = self._process_experience_doc(doc)
                    experiences.append(experience)

        except (RuntimeError, ValueError, AttributeError, KeyError) as e:
            # Firestore query errors, validation errors, or missing data fields
            logger.error(f"Error loading experiences (database/validation): {str(e)}")
            raise
        except Exception as e:
            # Unexpected errors - log with traceback and re-raise
            logger.error(
                f"Unexpected error loading experiences ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
            raise

        return experiences

    def _query_content_items(self, item_type: str, user_id: Optional[str] = None):
        """
        Query content-items collection (new schema).

        Args:
            item_type: Type of content item (company, project, skill-group, etc.)
            user_id: Optional user ID to filter by

        Returns:
            List of content item documents
        """
        query = self.db.collection("content-items").where(
            filter=FieldFilter("type", "==", item_type)
        )
        if user_id:
            query = query.where(filter=FieldFilter("userId", "==", user_id))

        return query.stream()

    def _query_experience_docs(self, user_id: Optional[str] = None):
        """
        Query experience documents from Firestore (old schema).

        Args:
            user_id: Optional user ID to filter by

        Returns:
            Stream of experience documents ordered by start date (descending)
        """
        query = self.db.collection("experience-entries")
        if user_id:
            query = query.where(filter=FieldFilter("userId", "==", user_id))

        # Order by start date descending (most recent first)
        query = query.order_by("startDate", direction=gcloud_firestore.Query.DESCENDING)

        return query.stream()

    def _process_content_item_doc(self, doc) -> Optional[Experience]:
        """
        Process a content-items document (new schema) into an Experience object.

        Args:
            doc: Firestore document snapshot with type='company'

        Returns:
            Experience object or None if invalid
        """
        data = doc.to_dict()

        # New schema has: company, role, technologies, accomplishments, etc.
        company = data.get("company", "")
        title = data.get("role", "")
        technologies = data.get("technologies", [])
        accomplishments = data.get("accomplishments", [])

        if not company or not title:
            logger.warning(f"Skipping content-item {doc.id}: missing company or role")
            return None

        # Build description from accomplishments
        description = "\n".join(accomplishments) if accomplishments else ""

        return Experience(
            company=company,
            title=title,
            start_date=data.get("startDate", ""),
            end_date=data.get("endDate"),
            location=data.get("location", ""),
            description=description,
            responsibilities=[],  # Could parse from accomplishments
            achievements=accomplishments,
            technologies=technologies,
            is_current=(data.get("endDate") is None or data.get("endDate") == ""),
        )

    def _process_experience_doc(self, doc) -> Experience:
        """
        Process a Firestore experience document into an Experience object.

        Args:
            doc: Firestore document snapshot

        Returns:
            Experience object

        Note:
            Firestore schema mapping:
            - title -> company name
            - role -> job title
            - body -> description (may contain "Stack: ..." section)
        """
        data = doc.to_dict()

        company = data.get("title", "")
        title = data.get("role", "")
        body = data.get("body", "")

        # Parse technologies from body (look for "Stack:" section)
        technologies = self._parse_technologies_from_body(body)

        # Map Firestore data to Experience model
        return Experience(
            company=company,
            title=title,
            start_date=data.get("startDate", ""),
            end_date=data.get("endDate"),
            location=data.get("location", ""),
            description=body,
            responsibilities=[],  # Not stored separately in Firestore
            achievements=[],  # Not stored separately in Firestore
            technologies=technologies,
            is_current=(data.get("endDate") is None or data.get("endDate") == ""),
        )

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

        Note: These are content sections (biography, education, etc.) for the
        portfolio website, not skill data. We keep this for potential summary
        generation but don't extract skills from it.
        """
        blurbs = []

        try:
            # Query experience-blurbs collection
            query = self.db.collection("experience-blurbs")
            if user_id:
                query = query.where(filter=FieldFilter("userId", "==", user_id))

            docs = query.stream()

            for doc in docs:
                data = doc.to_dict()
                blurbs.append(data)

        except (RuntimeError, ValueError, AttributeError) as e:
            # Firestore query errors or data access issues
            logger.error(f"Error loading experience blurbs (database): {str(e)}")
            raise
        except Exception as e:
            # Unexpected errors - log with traceback and re-raise
            logger.error(
                f"Unexpected error loading experience blurbs ({type(e).__name__}): {str(e)}",
                exc_info=True,
            )
            raise

        return blurbs

    def _extract_skills(
        self, experiences: List[Experience], blurbs: List[Dict[str, Any]]
    ) -> List[Skill]:
        """Extract and deduplicate skills from experiences and skill-group.

        Tries new schema (skill-group in content-items) first, then falls back
        to extracting from experience technologies.
        """
        skills_dict: Dict[str, Skill] = {}

        # Try loading from skill-group (new schema)
        try:
            skill_groups = list(self._query_content_items("skill-group"))
            if skill_groups:
                logger.info("Loading skills from skill-group")
                for group_doc in skill_groups:
                    group_data = group_doc.to_dict()
                    subcategories = group_data.get("subcategories", [])

                    for subcategory in subcategories:
                        category_name = subcategory.get("name", "")
                        skills = subcategory.get("skills", [])

                        for skill_name in skills:
                            if skill_name and skill_name not in skills_dict:
                                skills_dict[skill_name] = Skill(
                                    name=skill_name,
                                    level=None,
                                    years_experience=None,
                                    category=category_name or "technology",
                                )
        except Exception as e:
            logger.warning(
                f"Error loading skill-group, falling back to experience technologies: {e}"
            )

        # Also extract from experience technologies (for additional skills)
        for exp in experiences:
            for tech in exp.technologies:
                if tech and tech not in skills_dict:
                    skills_dict[tech] = Skill(
                        name=tech,
                        level=None,
                        years_experience=None,
                        category="technology",
                    )

        return list(skills_dict.values())

    def _generate_summary(self, experiences: List[Experience], blurbs: List[Dict[str, Any]]) -> str:
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
