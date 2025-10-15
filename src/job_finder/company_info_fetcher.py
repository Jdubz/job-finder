"""Company information fetcher using AI and web scraping."""

import logging
import requests
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)


class CompanyInfoFetcher:
    """Fetches and extracts company information from websites."""

    def __init__(self, ai_provider=None):
        """
        Initialize company info fetcher.

        Args:
            ai_provider: Optional AI provider for content extraction
        """
        self.ai_provider = ai_provider
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_company_info(self, company_name: str, company_website: str) -> Dict[str, Any]:
        """
        Fetch comprehensive company information.

        Args:
            company_name: Name of the company
            company_website: Company website URL

        Returns:
            Dictionary with company information:
            {
                'name': str,
                'website': str,
                'about': str,
                'culture': str,
                'mission': str,
                'size': str (optional),
                'industry': str (optional),
                'founded': str (optional)
            }
        """
        logger.info(f"Fetching company info for {company_name}")

        result = {
            'name': company_name,
            'website': company_website,
            'about': '',
            'culture': '',
            'mission': '',
            'size': '',
            'industry': '',
            'founded': ''
        }

        if not company_website:
            logger.warning(f"No website provided for {company_name}")
            return result

        try:
            # Try to fetch from common company pages
            pages_to_try = [
                f"{company_website}/about",
                f"{company_website}/about-us",
                f"{company_website}/company",
                f"{company_website}/careers",
                company_website,  # Homepage as fallback
            ]

            content = None
            for page_url in pages_to_try:
                try:
                    content = self._fetch_page_content(page_url)
                    if content and len(content) > 200:  # Got meaningful content
                        logger.info(f"Successfully fetched content from {page_url}")
                        break
                except Exception as e:
                    logger.debug(f"Failed to fetch {page_url}: {e}")
                    continue

            if content:
                # Extract information from content
                extracted = self._extract_company_info(content, company_name)
                result.update(extracted)

                logger.info(f"Extracted company info for {company_name}: "
                           f"{len(result['about'])} chars about, "
                           f"{len(result['culture'])} chars culture")
            else:
                logger.warning(f"Could not fetch any content for {company_name}")

        except Exception as e:
            logger.error(f"Error fetching company info for {company_name}: {e}")

        return result

    def _fetch_page_content(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        Fetch and clean page content.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Cleaned text content or None
        """
        try:
            # Normalize URL
            if not url.startswith('http'):
                url = f"https://{url}"

            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script, style, and other non-content tags
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            # Get text content
            text = soup.get_text(separator=' ', strip=True)

            # Clean up whitespace
            text = ' '.join(text.split())

            return text

        except requests.RequestException as e:
            logger.debug(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Error parsing {url}: {e}")
            return None

    def _extract_company_info(self, content: str, company_name: str) -> Dict[str, str]:
        """
        Extract company information from page content using AI or heuristics.

        Args:
            content: Page text content
            company_name: Company name

        Returns:
            Dictionary with extracted fields
        """
        result = {
            'about': '',
            'culture': '',
            'mission': '',
            'size': '',
            'industry': '',
            'founded': ''
        }

        # If we have AI provider, use it for better extraction
        if self.ai_provider:
            result = self._extract_with_ai(content, company_name)
        else:
            # Fallback to simple heuristics
            result = self._extract_with_heuristics(content)

        return result

    def _extract_with_ai(self, content: str, company_name: str) -> Dict[str, str]:
        """
        Use AI to extract company information from content.

        Args:
            content: Page text content
            company_name: Company name

        Returns:
            Dictionary with extracted fields
        """
        try:
            # Truncate content to reasonable length for AI
            max_chars = 5000
            truncated_content = content[:max_chars]

            prompt = f"""Extract company information from the following text about {company_name}.

Company Website Content:
{truncated_content}

Extract the following information and return as JSON:
1. "about": 2-3 sentence summary of what the company does
2. "culture": 1-2 sentences about company culture, values, or work environment
3. "mission": Company mission statement if mentioned (or empty string)
4. "size": Company size/employees if mentioned (e.g., "500-1000 employees")
5. "industry": Industry/sector (e.g., "Fintech", "E-commerce", "SaaS")
6. "founded": Year founded if mentioned

Be concise and factual. If information is not found, use empty string.

Return ONLY valid JSON in this format:
{{
  "about": "...",
  "culture": "...",
  "mission": "...",
  "size": "...",
  "industry": "...",
  "founded": "..."
}}"""

            response = self.ai_provider.generate(prompt, max_tokens=1000, temperature=0.2)

            # Parse JSON response
            import json
            response_clean = response.strip()
            if "```json" in response_clean:
                start = response_clean.find("```json") + 7
                end = response_clean.find("```", start)
                response_clean = response_clean[start:end].strip()
            elif "```" in response_clean:
                start = response_clean.find("```") + 3
                end = response_clean.find("```", start)
                response_clean = response_clean[start:end].strip()

            extracted = json.loads(response_clean)
            logger.info(f"AI extracted company info successfully")
            return extracted

        except Exception as e:
            logger.warning(f"AI extraction failed, falling back to heuristics: {e}")
            return self._extract_with_heuristics(content)

    def _extract_with_heuristics(self, content: str) -> Dict[str, str]:
        """
        Extract company info using simple heuristics (fallback).

        Args:
            content: Page text content

        Returns:
            Dictionary with extracted fields
        """
        result = {
            'about': '',
            'culture': '',
            'mission': '',
            'size': '',
            'industry': '',
            'founded': ''
        }

        # Try to find common patterns
        content_lower = content.lower()

        # Look for mission/about sections
        keywords = {
            'mission': ['our mission', 'mission statement', 'our purpose'],
            'culture': ['our culture', 'our values', 'work environment', 'company culture'],
            'about': ['about us', 'who we are', 'what we do'],
        }

        for field, patterns in keywords.items():
            for pattern in patterns:
                if pattern in content_lower:
                    # Find the section and extract a snippet
                    start_idx = content_lower.find(pattern)
                    snippet = content[start_idx:start_idx + 500]

                    # Clean and truncate
                    snippet = ' '.join(snippet.split())[:300]
                    result[field] = snippet
                    break

        # If we found nothing, use first 300 chars as about
        if not result['about'] and len(content) > 100:
            result['about'] = content[:300].strip()

        return result


def create_company_info_fetcher(ai_provider=None) -> CompanyInfoFetcher:
    """
    Factory function to create a CompanyInfoFetcher.

    Args:
        ai_provider: Optional AI provider for intelligent extraction

    Returns:
        CompanyInfoFetcher instance
    """
    return CompanyInfoFetcher(ai_provider=ai_provider)
