"""Tests for job filtering logic."""

import pytest

from job_finder.filters import JobFilter


class TestJobFilterInit:
    """Test JobFilter initialization."""

    def test_init_with_config(self):
        """Test initialization with config."""
        config = {"profile": {"keywords": ["python"], "preferred_locations": ["remote"]}}
        filter_obj = JobFilter(config)
        assert filter_obj.config == config

    def test_init_with_empty_config(self):
        """Test initialization with empty config."""
        config = {}
        filter_obj = JobFilter(config)
        assert filter_obj.config == {}


class TestFilterByWorkLocation:
    """Test work location filtering (remote/Portland hybrid)."""

    @pytest.fixture
    def filter_obj(self):
        """Create a JobFilter instance."""
        return JobFilter({})

    def test_filter_remote_in_location(self, filter_obj):
        """Test remote keyword in location field."""
        jobs = [
            {"title": "Engineer", "location": "Remote - US", "description": "Job desc"},
            {"title": "Engineer", "location": "San Francisco, CA", "description": "Job desc"},
        ]
        filtered = filter_obj._filter_by_work_location(jobs)
        assert len(filtered) == 1
        assert filtered[0]["location"] == "Remote - US"

    def test_filter_remote_in_description(self, filter_obj):
        """Test remote keyword in description."""
        jobs = [
            {"title": "Engineer", "location": "US", "description": "This is a remote position"},
            {"title": "Engineer", "location": "NYC", "description": "Office position"},
        ]
        filtered = filter_obj._filter_by_work_location(jobs)
        assert len(filtered) == 1
        assert "remote position" in filtered[0]["description"]

    def test_filter_remote_in_title(self, filter_obj):
        """Test remote keyword in title."""
        jobs = [
            {"title": "Remote Software Engineer", "location": "US", "description": "Job desc"},
            {"title": "Software Engineer", "location": "NYC", "description": "Job desc"},
        ]
        filtered = filter_obj._filter_by_work_location(jobs)
        assert len(filtered) == 1
        assert "Remote" in filtered[0]["title"]

    def test_filter_work_from_home_in_description(self, filter_obj):
        """Test 'work from home' in description."""
        jobs = [
            {"title": "Engineer", "location": "US", "description": "Work from home available"},
            {"title": "Engineer", "location": "NYC", "description": "Office based"},
        ]
        filtered = filter_obj._filter_by_work_location(jobs)
        assert len(filtered) == 1

    def test_filter_wfh_in_description(self, filter_obj):
        """Test 'wfh' abbreviation in description."""
        jobs = [
            {"title": "Engineer", "location": "US", "description": "WFH position"},
            {"title": "Engineer", "location": "NYC", "description": "Office based"},
        ]
        filtered = filter_obj._filter_by_work_location(jobs)
        assert len(filtered) == 1

    def test_filter_portland_hybrid(self, filter_obj):
        """Test Portland, OR hybrid jobs are included."""
        jobs = [
            {
                "title": "Engineer",
                "location": "Portland, OR",
                "description": "Hybrid position - 2 days/week in office",
            },
            {"title": "Engineer", "location": "Portland, OR", "description": "Full-time office"},
        ]
        filtered = filter_obj._filter_by_work_location(jobs)
        assert len(filtered) == 1
        assert "Hybrid position" in filtered[0]["description"]

    def test_filter_portland_with_oregon(self, filter_obj):
        """Test Portland with Oregon spelled out."""
        jobs = [
            {
                "title": "Hybrid Engineer",
                "location": "Portland, Oregon",
                "description": "Job desc",
            },
        ]
        filtered = filter_obj._filter_by_work_location(jobs)
        assert len(filtered) == 1

    def test_filter_hybrid_in_title(self, filter_obj):
        """Test hybrid in title for Portland jobs."""
        jobs = [
            {"title": "Hybrid Software Engineer", "location": "Portland, OR", "description": "Job"},
        ]
        filtered = filter_obj._filter_by_work_location(jobs)
        assert len(filtered) == 1

    def test_filter_excludes_portland_non_hybrid(self, filter_obj):
        """Test Portland non-hybrid jobs are excluded."""
        jobs = [
            {"title": "Engineer", "location": "Portland, OR", "description": "Full-time office"},
        ]
        filtered = filter_obj._filter_by_work_location(jobs)
        assert len(filtered) == 0

    def test_filter_excludes_non_portland_hybrid(self, filter_obj):
        """Test non-Portland hybrid jobs are excluded."""
        jobs = [
            {"title": "Engineer", "location": "Seattle, WA", "description": "Hybrid position"},
        ]
        filtered = filter_obj._filter_by_work_location(jobs)
        assert len(filtered) == 0

    def test_filter_case_insensitive(self, filter_obj):
        """Test filtering is case-insensitive."""
        jobs = [
            {"title": "ENGINEER", "location": "REMOTE - US", "description": "JOB DESC"},
        ]
        filtered = filter_obj._filter_by_work_location(jobs)
        assert len(filtered) == 1

    def test_filter_empty_jobs_list(self, filter_obj):
        """Test filtering empty jobs list."""
        filtered = filter_obj._filter_by_work_location([])
        assert filtered == []

    def test_filter_missing_fields(self, filter_obj):
        """Test filtering jobs with missing fields."""
        jobs = [
            {"title": "Engineer"},  # Missing location and description
            {},  # Empty job
        ]
        filtered = filter_obj._filter_by_work_location(jobs)
        assert len(filtered) == 0


class TestFilterByKeywords:
    """Test keyword filtering."""

    @pytest.fixture
    def filter_obj(self):
        """Create a JobFilter instance."""
        return JobFilter({})

    def test_filter_keyword_in_title(self, filter_obj):
        """Test keyword found in title."""
        jobs = [
            {"title": "Python Developer", "description": "Job description"},
            {"title": "Java Developer", "description": "Job description"},
        ]
        filtered = filter_obj._filter_by_keywords(jobs, ["python"])
        assert len(filtered) == 1
        assert "Python" in filtered[0]["title"]

    def test_filter_keyword_in_description(self, filter_obj):
        """Test keyword found in description."""
        jobs = [
            {"title": "Developer", "description": "Looking for Python experience"},
            {"title": "Developer", "description": "Looking for Java experience"},
        ]
        filtered = filter_obj._filter_by_keywords(jobs, ["python"])
        assert len(filtered) == 1

    def test_filter_multiple_keywords(self, filter_obj):
        """Test multiple keywords (OR logic)."""
        jobs = [
            {"title": "Python Developer", "description": "Job desc"},
            {"title": "JavaScript Developer", "description": "Job desc"},
            {"title": "Java Developer", "description": "Job desc"},
        ]
        filtered = filter_obj._filter_by_keywords(jobs, ["python", "javascript"])
        assert len(filtered) == 2

    def test_filter_case_insensitive_keywords(self, filter_obj):
        """Test keyword matching is case-insensitive."""
        jobs = [
            {"title": "PYTHON DEVELOPER", "description": "Job desc"},
        ]
        filtered = filter_obj._filter_by_keywords(jobs, ["python"])
        assert len(filtered) == 1

    def test_filter_empty_keywords(self, filter_obj):
        """Test filtering with empty keywords list."""
        jobs = [
            {"title": "Developer", "description": "Job desc"},
        ]
        filtered = filter_obj._filter_by_keywords(jobs, [])
        assert len(filtered) == 0

    def test_filter_no_matching_keywords(self, filter_obj):
        """Test no jobs match keywords."""
        jobs = [
            {"title": "Java Developer", "description": "Job desc"},
        ]
        filtered = filter_obj._filter_by_keywords(jobs, ["python"])
        assert len(filtered) == 0


class TestFilterByLocation:
    """Test location filtering."""

    @pytest.fixture
    def filter_obj(self):
        """Create a JobFilter instance."""
        return JobFilter({})

    def test_filter_single_location(self, filter_obj):
        """Test filtering by single location."""
        jobs = [
            {"title": "Engineer", "location": "San Francisco, CA", "description": "Job desc"},
            {"title": "Engineer", "location": "New York, NY", "description": "Job desc"},
        ]
        filtered = filter_obj._filter_by_location(jobs, ["San Francisco"])
        assert len(filtered) == 1
        assert "San Francisco" in filtered[0]["location"]

    def test_filter_multiple_locations(self, filter_obj):
        """Test filtering by multiple locations."""
        jobs = [
            {"title": "Engineer", "location": "San Francisco, CA", "description": "Job desc"},
            {"title": "Engineer", "location": "New York, NY", "description": "Job desc"},
            {"title": "Engineer", "location": "Chicago, IL", "description": "Job desc"},
        ]
        filtered = filter_obj._filter_by_location(jobs, ["San Francisco", "New York"])
        assert len(filtered) == 2

    def test_filter_location_case_insensitive(self, filter_obj):
        """Test location filtering is case-insensitive."""
        jobs = [
            {"title": "Engineer", "location": "SAN FRANCISCO, CA", "description": "Job desc"},
        ]
        filtered = filter_obj._filter_by_location(jobs, ["san francisco"])
        assert len(filtered) == 1

    def test_filter_remote_location(self, filter_obj):
        """Test filtering by 'remote' location."""
        jobs = [
            {"title": "Engineer", "location": "Remote - US", "description": "Job desc"},
            {"title": "Engineer", "location": "San Francisco, CA", "description": "Job desc"},
        ]
        filtered = filter_obj._filter_by_location(jobs, ["remote"])
        assert len(filtered) == 1

    def test_filter_empty_locations(self, filter_obj):
        """Test filtering with empty locations list."""
        jobs = [
            {"title": "Engineer", "location": "San Francisco, CA", "description": "Job desc"},
        ]
        filtered = filter_obj._filter_by_location(jobs, [])
        assert len(filtered) == 0


class TestExcludeByKeywords:
    """Test keyword exclusion."""

    @pytest.fixture
    def filter_obj(self):
        """Create a JobFilter instance."""
        return JobFilter({})

    def test_exclude_keyword_in_title(self, filter_obj):
        """Test excluding jobs with keyword in title."""
        jobs = [
            {"title": "Junior Python Developer", "description": "Job desc"},
            {"title": "Senior Python Developer", "description": "Job desc"},
        ]
        filtered = filter_obj._exclude_by_keywords(jobs, ["junior"])
        assert len(filtered) == 1
        assert "Senior" in filtered[0]["title"]

    def test_exclude_keyword_in_description(self, filter_obj):
        """Test excluding jobs with keyword in description."""
        jobs = [
            {"title": "Developer", "description": "Junior level position"},
            {"title": "Developer", "description": "Senior level position"},
        ]
        filtered = filter_obj._exclude_by_keywords(jobs, ["junior"])
        assert len(filtered) == 1

    def test_exclude_multiple_keywords(self, filter_obj):
        """Test excluding multiple keywords."""
        jobs = [
            {"title": "Junior Developer", "description": "Job desc"},
            {"title": "Intern Developer", "description": "Job desc"},
            {"title": "Senior Developer", "description": "Job desc"},
        ]
        filtered = filter_obj._exclude_by_keywords(jobs, ["junior", "intern"])
        assert len(filtered) == 1
        assert "Senior" in filtered[0]["title"]

    def test_exclude_case_insensitive(self, filter_obj):
        """Test exclusion is case-insensitive."""
        jobs = [
            {"title": "JUNIOR DEVELOPER", "description": "Job desc"},
        ]
        filtered = filter_obj._exclude_by_keywords(jobs, ["junior"])
        assert len(filtered) == 0

    def test_exclude_empty_keywords(self, filter_obj):
        """Test exclusion with empty keywords list."""
        jobs = [
            {"title": "Developer", "description": "Job desc"},
        ]
        filtered = filter_obj._exclude_by_keywords(jobs, [])
        assert len(filtered) == 1


class TestFilterJobs:
    """Test main filter_jobs method."""

    def test_filter_jobs_with_all_filters(self):
        """Test applying all filters together."""
        config = {
            "profile": {
                "keywords": ["python"],
                "preferred_locations": ["remote"],
                "excluded_keywords": ["junior"],
            }
        }
        filter_obj = JobFilter(config)

        jobs = [
            {
                "title": "Senior Python Developer",
                "location": "Remote - US",
                "description": "Looking for Python experience",
            },
            {
                "title": "Junior Python Developer",
                "location": "Remote - US",
                "description": "Entry level",
            },
            {
                "title": "Senior Java Developer",
                "location": "Remote - US",
                "description": "Looking for Java experience",
            },
            {
                "title": "Senior Python Developer",
                "location": "San Francisco, CA",
                "description": "Office position",
            },
        ]

        filtered = filter_obj.filter_jobs(jobs)

        # Should only include: Senior Python Developer, Remote
        assert len(filtered) == 1
        assert filtered[0]["title"] == "Senior Python Developer"
        assert "Remote" in filtered[0]["location"]

    def test_filter_jobs_with_no_optional_filters(self):
        """Test filtering with only work location filter."""
        config = {"profile": {}}
        filter_obj = JobFilter(config)

        jobs = [
            {"title": "Engineer", "location": "Remote - US", "description": "Job desc"},
            {"title": "Engineer", "location": "San Francisco, CA", "description": "Job desc"},
        ]

        filtered = filter_obj.filter_jobs(jobs)

        # Should only apply work location filter
        assert len(filtered) == 1
        assert "Remote" in filtered[0]["location"]

    def test_filter_jobs_with_keywords_only(self):
        """Test filtering with keywords only."""
        config = {"profile": {"keywords": ["python"]}}
        filter_obj = JobFilter(config)

        jobs = [
            {"title": "Python Developer", "location": "Remote - US", "description": "Job desc"},
            {"title": "Java Developer", "location": "Remote - US", "description": "Job desc"},
        ]

        filtered = filter_obj.filter_jobs(jobs)

        assert len(filtered) == 1
        assert "Python" in filtered[0]["title"]

    def test_filter_jobs_with_locations_only(self):
        """Test filtering with locations only."""
        config = {"profile": {"preferred_locations": ["san francisco"]}}
        filter_obj = JobFilter(config)

        jobs = [
            {
                "title": "Engineer",
                "location": "Remote - San Francisco",
                "description": "Job desc",
            },
            {"title": "Engineer", "location": "Remote - New York", "description": "Job desc"},
        ]

        filtered = filter_obj.filter_jobs(jobs)

        assert len(filtered) == 1
        assert "San Francisco" in filtered[0]["location"]

    def test_filter_jobs_with_exclusions_only(self):
        """Test filtering with exclusions only."""
        config = {"profile": {"excluded_keywords": ["junior"]}}
        filter_obj = JobFilter(config)

        jobs = [
            {"title": "Junior Engineer", "location": "Remote - US", "description": "Job desc"},
            {"title": "Senior Engineer", "location": "Remote - US", "description": "Job desc"},
        ]

        filtered = filter_obj.filter_jobs(jobs)

        assert len(filtered) == 1
        assert "Senior" in filtered[0]["title"]

    def test_filter_jobs_empty_list(self):
        """Test filtering empty jobs list."""
        config = {"profile": {"keywords": ["python"]}}
        filter_obj = JobFilter(config)

        filtered = filter_obj.filter_jobs([])
        assert filtered == []

    def test_filter_jobs_all_filtered_out(self):
        """Test when all jobs are filtered out."""
        config = {"profile": {"keywords": ["python"]}}
        filter_obj = JobFilter(config)

        jobs = [
            {"title": "Java Developer", "location": "Remote - US", "description": "Java only"},
        ]

        filtered = filter_obj.filter_jobs(jobs)
        assert filtered == []
