"""E2E test scenarios for Portfolio + Job-Finder integration."""

from .base_scenario import BaseE2EScenario, TestResult, TestStatus
from .scenario_01_job_submission import JobSubmissionScenario
from .scenario_02_filtered_job import FilteredJobScenario

__all__ = [
    "BaseE2EScenario",
    "TestResult",
    "TestStatus",
    "JobSubmissionScenario",
    "FilteredJobScenario",
]
