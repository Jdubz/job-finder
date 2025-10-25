"""AI-powered CSS selector discovery for job scraping."""

import json
import logging
from typing import Any, Dict, Optional

from job_finder.ai.providers import AITask, create_provider
from job_finder.constants import MAX_HTML_SAMPLE_LENGTH

logger = logging.getLogger(__name__)


class SelectorDiscovery:
    """
    Uses AI to discover CSS selectors for scraping job listings.

    This is used when:
    1. Adding a new job source without known selectors
    2. Existing selectors fail (page structure changed)
    3. Validating/improving existing selectors
    """

    def __init__(self, provider_type: str = "claude", api_key: Optional[str] = None):
        """
        Initialize selector discovery.

        Args:
            provider_type: AI provider to use (claude, openai)
            api_key: Optional API key (uses env var if not provided)
        """
        self.provider = create_provider(
            provider_type=provider_type, api_key=api_key, task=AITask.SELECTOR_DISCOVERY
        )

    def discover_selectors(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Discover CSS selectors for a job board page.

        Args:
            html: Raw HTML of the job listing page
            url: URL of the page (for context)

        Returns:
            Dictionary with discovered selectors, or None if discovery failed

        Example return value:
        {
            "job_list_container": ".jobs-list",
            "job_item": ".job-card",
            "title": ".job-title",
            "company": ".company-name",
            "location": ".location",
            "description": ".job-description",
            "apply_url": "a.apply-button",
            "posted_date": ".posted-date",
            "salary": ".salary-range",
            "confidence": "high",
            "notes": "Standard job board layout with clear semantic classes"
        }
        """
        prompt = self._build_discovery_prompt(html, url)

        try:
            response = self.provider.generate(prompt, max_tokens=1500, temperature=0.1)
            result = self._parse_discovery_response(response)

            if result:
                logger.info(
                    f"Discovered selectors for {url} with {result.get('confidence', 'unknown')} confidence"
                )
            else:
                logger.warning(f"Failed to discover selectors for {url}")

            return result

        except Exception as e:
            logger.error(f"Error discovering selectors: {e}")
            return None

    def _build_discovery_prompt(self, html: str, url: str) -> str:
        """Build prompt for selector discovery."""
        # Truncate HTML if too long (keep first 20k chars)
        html_sample = html[:MAX_HTML_SAMPLE_LENGTH] if len(html) > MAX_HTML_SAMPLE_LENGTH else html

        return f"""You are an expert at analyzing HTML structure to extract CSS selectors for web scraping.

Analyze this job listing page and identify the CSS selectors needed to scrape job postings.

URL: {url}

HTML Sample:
```html
{html_sample}
```

Identify selectors for these fields (mark as null if not found):
- job_list_container: Container element holding all job listings
- job_item: Individual job listing element (relative to container)
- title: Job title
- company: Company name
- location: Job location
- description: Job description (full text or preview)
- apply_url: Link to apply or full job posting
- posted_date: When job was posted
- salary: Salary range/information
- job_type: Employment type (full-time, contract, etc.)

Also provide:
- confidence: "high", "medium", or "low" based on page structure clarity
- notes: Brief explanation of the page structure and any challenges

Return ONLY a valid JSON object with this structure:
{{
    "job_list_container": ".selector or null",
    "job_item": ".selector or null",
    "title": ".selector or null",
    "company": ".selector or null",
    "location": ".selector or null",
    "description": ".selector or null",
    "apply_url": "a.selector or null",
    "posted_date": ".selector or null",
    "salary": ".selector or null",
    "job_type": ".selector or null",
    "confidence": "high|medium|low",
    "notes": "explanation"
}}

Important:
- Use CSS selectors that are specific but not overly fragile
- Prefer semantic classes over generic ones (e.g., .job-title over .item-1)
- For links, include the tag (e.g., "a.apply-button")
- Return null for fields that don't exist on this page
- Be concise in your notes"""

    def _parse_discovery_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse AI response for selector discovery.

        Args:
            response: Raw AI response

        Returns:
            Parsed selectors dict, or None if parsing failed
        """
        try:
            # Try to extract JSON from response (handle markdown code blocks)
            response = response.strip()

            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                # Remove first line (```json) and last line (```)
                response = "\n".join(lines[1:-1])

            result = json.loads(response)

            # Validate required fields
            required_fields = ["confidence", "notes"]
            if not all(field in result for field in required_fields):
                logger.warning("Discovery response missing required fields")
                return None

            # Convert empty strings to None
            for key, value in result.items():
                if value == "" or value == "null":
                    result[key] = None

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse discovery response as JSON: {e}")
            logger.debug(f"Response was: {response[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error parsing discovery response: {e}")
            return None
