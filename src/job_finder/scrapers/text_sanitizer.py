"""Text sanitization utilities for cleaning scraped content."""

import html
import re
import unicodedata
from typing import Optional


def sanitize_text(text: Optional[str], max_length: Optional[int] = None) -> str:
    """
    Comprehensive text sanitization for scraped content.

    Handles:
    - HTML entity decoding (e.g., &amp; → &, &#8217; → ')
    - HTML tag removal
    - Unicode normalization
    - Smart quotes and special characters
    - Excessive whitespace
    - Invisible characters

    Args:
        text: Raw text to sanitize
        max_length: Optional maximum length to truncate to

    Returns:
        Clean, normalized text
    """
    if not text:
        return ""

    # 1. Decode HTML entities (handles all entities, not just common ones)
    text = html.unescape(text)

    # 2. Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # 3. Normalize Unicode characters (NFC = Canonical Decomposition + Canonical Composition)
    text = unicodedata.normalize("NFC", text)

    # 4. Replace smart quotes and special punctuation with ASCII equivalents
    replacements = {
        # Smart quotes
        "\u2018": "'",  # Left single quotation mark
        "\u2019": "'",  # Right single quotation mark
        "\u201c": '"',  # Left double quotation mark
        "\u201d": '"',  # Right double quotation mark
        # Dashes
        "\u2013": "-",  # En dash
        "\u2014": "-",  # Em dash
        "\u2015": "-",  # Horizontal bar
        # Ellipsis
        "\u2026": "...",  # Horizontal ellipsis
        # Bullets
        "\u2022": "*",  # Bullet
        "\u2023": "*",  # Triangular bullet
        # Spaces
        "\xa0": " ",  # Non-breaking space
        "\u200b": "",  # Zero-width space
        "\u200c": "",  # Zero-width non-joiner
        "\u200d": "",  # Zero-width joiner
        "\ufeff": "",  # Zero-width no-break space (BOM)
        # Other common symbols
        "\u00a9": "(c)",  # Copyright symbol
        "\u00ae": "(R)",  # Registered trademark
        "\u2122": "(TM)",  # Trademark symbol
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # 5. Remove any remaining control characters except newlines and tabs
    text = "".join(char for char in text if unicodedata.category(char)[0] != "C" or char in "\n\t")

    # 6. Normalize whitespace
    # Replace multiple spaces with single space
    text = re.sub(r"[ \t]+", " ", text)
    # Replace multiple newlines with double newline (preserve paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove spaces at line boundaries
    text = re.sub(r" *\n *", "\n", text)

    # 7. Trim whitespace
    text = text.strip()

    # 8. Truncate if requested
    if max_length and len(text) > max_length:
        text = text[:max_length].rsplit(" ", 1)[0] + "..."

    return text


def sanitize_html_description(html_text: str) -> str:
    """
    Sanitize HTML job descriptions while preserving some structure.

    Converts HTML to plain text while:
    - Preserving paragraph breaks
    - Converting lists to bullet points
    - Removing excessive formatting

    Args:
        html_text: HTML content

    Returns:
        Clean plain text with preserved structure
    """
    if not html_text:
        return ""

    # Convert <br> and <p> tags to newlines before removing tags
    text = re.sub(r"<br\s*/?>", "\n", html_text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "", text, flags=re.IGNORECASE)

    # Convert list items to bullets
    text = re.sub(r"<li[^>]*>", "\n* ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "", text, flags=re.IGNORECASE)

    # Convert headers to emphasized text with newlines
    text = re.sub(r"<h[1-6][^>]*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</h[1-6]>", "\n", text, flags=re.IGNORECASE)

    # Now apply standard sanitization
    return sanitize_text(text)


def sanitize_title(title: str) -> str:
    """
    Sanitize job title.

    Args:
        title: Raw job title

    Returns:
        Clean job title
    """
    if not title:
        return ""

    # Sanitize text
    title = sanitize_text(title)

    # Remove extra punctuation at the end
    title = re.sub(r"[,;:\-\s]+$", "", title)

    return title.strip()


def sanitize_company_name(company: str) -> str:
    """
    Sanitize company name.

    Args:
        company: Raw company name

    Returns:
        Clean company name
    """
    if not company:
        return ""

    # Sanitize text
    company = sanitize_text(company)

    # Remove common suffixes if they're duplicated
    # e.g., "Acme Inc. Inc." -> "Acme Inc."
    suffixes = ["Inc.", "LLC", "Ltd.", "Corp.", "Corporation", "Company", "Co."]
    for suffix in suffixes:
        # Match the suffix appearing twice with optional space between
        pattern = rf"(\b{re.escape(suffix)})\s+\1\b"
        company = re.sub(pattern, r"\1", company, flags=re.IGNORECASE)

    return company.strip()
