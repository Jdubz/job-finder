"""Tests for text sanitization utilities."""

from job_finder.scrapers.text_sanitizer import (
    sanitize_company_name,
    sanitize_html_description,
    sanitize_text,
    sanitize_title,
)


def test_sanitize_html_entities():
    """Test HTML entity decoding."""
    text = "We&rsquo;re hiring &amp; growing! Join us&#8212;apply today."
    result = sanitize_text(text)
    assert result == "We're hiring & growing! Join us-apply today."


def test_sanitize_smart_quotes():
    """Test smart quote normalization."""
    text = "\u201cGreat opportunity\u201d at \u2018Top Company\u2019"
    result = sanitize_text(text)
    assert result == "\"Great opportunity\" at 'Top Company'"


def test_sanitize_unicode_dashes():
    """Test em dash and en dash normalization."""
    text = "Full-time \u2014 Remote \u2013 $100k-$150k"
    result = sanitize_text(text)
    assert result == "Full-time - Remote - $100k-$150k"


def test_sanitize_html_description():
    """Test HTML description sanitization with structure preservation."""
    html = """
    <p>We're looking for a <strong>Senior Engineer</strong>!</p>
    <br/>
    <h2>Requirements:</h2>
    <ul>
        <li>5+ years experience</li>
        <li>Python &amp; JavaScript</li>
    </ul>
    """
    result = sanitize_html_description(html)

    # Should preserve structure
    assert "We're looking for a Senior Engineer!" in result
    assert "Requirements:" in result
    assert "* 5+ years experience" in result
    assert "* Python & JavaScript" in result
    # Should not have HTML tags
    assert "<p>" not in result
    assert "<li>" not in result


def test_sanitize_title():
    """Test job title sanitization."""
    # Test with trailing punctuation
    title = "Senior Software Engineer - "
    result = sanitize_title(title)
    assert result == "Senior Software Engineer"

    # Test with HTML entities
    title = "Full&ndash;Stack Developer"
    result = sanitize_title(title)
    assert result == "Full-Stack Developer"


def test_sanitize_company_name():
    """Test company name sanitization."""
    # Test with HTML entities
    company = "Tech&nbsp;Solutions LLC"
    result = sanitize_company_name(company)
    assert result == "Tech Solutions LLC"

    # Test with smart quotes
    company = "\u201cInnovative\u201d Tech Corp"
    result = sanitize_company_name(company)
    assert result == '"Innovative" Tech Corp'


def test_sanitize_invisible_characters():
    """Test removal of invisible characters."""
    # Zero-width spaces and non-breaking spaces
    text = "Hello\u200bWorld\xa0Company"
    result = sanitize_text(text)
    assert result == "HelloWorld Company"


def test_sanitize_excessive_whitespace():
    """Test whitespace normalization."""
    text = "Senior    Engineer\n\n\n\nRemote    Position"
    result = sanitize_text(text)
    assert result == "Senior Engineer\n\nRemote Position"


def test_sanitize_special_symbols():
    """Test special symbol conversion."""
    text = "\u2022 Feature 1\n\u2022 Feature 2"
    result = sanitize_text(text)
    assert "* Feature 1" in result
    assert "* Feature 2" in result


def test_sanitize_empty_text():
    """Test handling of empty/None text."""
    assert sanitize_text(None) == ""
    assert sanitize_text("") == ""
    assert sanitize_title("") == ""
    assert sanitize_company_name("") == ""
    assert sanitize_html_description("") == ""
    assert sanitize_html_description(None) == ""


def test_sanitize_max_length():
    """Test text truncation."""
    long_text = "This is a very long description that should be truncated " * 10
    result = sanitize_text(long_text, max_length=50)
    assert len(result) <= 53  # 50 + "..."
    assert result.endswith("...")
