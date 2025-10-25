"""Tests for company name normalization utilities."""

from job_finder.utils.company_name_utils import normalize_company_name


class TestNormalizeCompanyName:
    """Test company name normalization."""

    def test_removes_careers_suffix(self):
        """Should remove 'Careers' suffix."""
        assert normalize_company_name("Cloudflare Careers") == "cloudflare"
        assert normalize_company_name("Google Career") == "google"

    def test_removes_jobs_suffix(self):
        """Should remove 'Jobs' suffix."""
        assert normalize_company_name("Microsoft Jobs") == "microsoft"
        assert normalize_company_name("Apple Job") == "apple"

    def test_removes_legal_entity_suffixes(self):
        """Should remove legal entity suffixes."""
        assert normalize_company_name("Netflix Inc.") == "netflix"
        assert normalize_company_name("Amazon Corporation") == "amazon"
        assert normalize_company_name("Stripe LLC") == "stripe"
        assert normalize_company_name("Shopify Ltd") == "shopify"

    def test_removes_combined_suffixes(self):
        """Should handle multiple suffixes."""
        assert normalize_company_name("Datadog Inc. Careers") == "datadog"
        assert normalize_company_name("GitHub Corp Jobs") == "github"

    def test_handles_dash_separator(self):
        """Should remove dash-separated careers."""
        assert normalize_company_name("Spotify - Careers") == "spotify"
        assert normalize_company_name("Reddit | Careers") == "reddit"

    def test_case_insensitive(self):
        """Should convert to lowercase."""
        assert normalize_company_name("CLOUDFLARE") == "cloudflare"
        assert normalize_company_name("CloudFlare") == "cloudflare"

    def test_preserves_company_name(self):
        """Should preserve actual company name without suffixes."""
        assert normalize_company_name("Cloudflare") == "cloudflare"
        assert normalize_company_name("Google") == "google"
        assert normalize_company_name("Microsoft") == "microsoft"

    def test_handles_empty_string(self):
        """Should handle empty strings."""
        assert normalize_company_name("") == ""
        assert normalize_company_name("   ") == ""

    def test_removes_extra_whitespace(self):
        """Should normalize whitespace."""
        assert normalize_company_name("  Cloudflare  Careers  ") == "cloudflare"
        assert normalize_company_name("Google   Jobs") == "google"

    def test_deduplication_examples(self):
        """Test real-world deduplication scenarios."""
        # These should all normalize to the same value
        cloudflare_variants = [
            "Cloudflare",
            "cloudflare",
            "Cloudflare Careers",
            "Cloudflare Jobs",
            "Cloudflare Inc.",
            "Cloudflare, Inc.",
        ]

        normalized_values = [normalize_company_name(name) for name in cloudflare_variants]

        # All should be the same
        assert len(set(normalized_values)) == 1
        assert normalized_values[0] == "cloudflare"
