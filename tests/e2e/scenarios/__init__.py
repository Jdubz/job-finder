"""E2E test scenarios for job-finder-FE + Job-Finder integration."""

from .base_scenario import BaseE2EScenario, TestResult, TestStatus
from .scenario_01_job_submission import JobSubmissionScenario
from .scenario_02_filtered_job import FilteredJobScenario
from .scenario_03_company_source_discovery import CompanySourceDiscoveryScenario
from .scenario_04_scrape_rotation import ScrapeRotationScenario
from .scenario_05_full_discovery_cycle import FullDiscoveryCycleScenario

__all__ = [
    "BaseE2EScenario",
    "TestResult",
    "TestStatus",
    "JobSubmissionScenario",
    "FilteredJobScenario",
    "CompanySourceDiscoveryScenario",
    "ScrapeRotationScenario",
    "FullDiscoveryCycleScenario",
]
