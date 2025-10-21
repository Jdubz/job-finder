# Job Finder - Makefile
# AI-powered job matching and scraping tool
#
# Usage: make [target]
# Run 'make help' to see all available targets

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
FLAKE8 := $(PYTHON) -m flake8
MYPY := $(PYTHON) -m mypy
DOCKER := docker
DOCKER_COMPOSE := docker compose
DOCKER_IMAGE := job-finder
DOCKER_REGISTRY := ghcr.io/jdubz
ENV_FILE := .env
VENV_DIR := venv
SRC_DIR := src
TEST_DIR := tests
SCRIPTS_DIR := scripts

# Color codes for output
RESET := \033[0m
BOLD := \033[1m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
CYAN := \033[36m

# ============================================================================
# DEPRECATION NOTICE
# ============================================================================
# 📢 New workflow available: dev-monitor Scripts Panel
#
# For build, test, and quality commands, use the dev-monitor UI:
#   http://localhost:5174 → Scripts tab
#
# Benefits:
#   ✅ One-click execution across all repos
#   ✅ Real-time output streaming
#   ✅ Execution history tracking
#   ✅ No context switching between terminals
#
# These Makefiles will remain functional for backward compatibility
# and local development commands (dev, docker-*, db-*).
# ============================================================================

# Default target
.DEFAULT_GOAL := help

# Mark targets that don't create files
.PHONY: help setup install dev-install dev dev-stop dev-status dev-logs clean test test-coverage test-e2e test-e2e-full test-e2e-local test-e2e-local-verbose test-e2e-local-full lint format type-check \
        run search docker-build docker-push docker-run docker-up docker-down docker-logs \
        db-explore db-cleanup db-merge-companies db-setup-listings db-setup-config worker scheduler \
        deploy-staging deploy-production clean-cache clean-all

## === Help & Information ===

help: ## Show this help message
	@echo "$(BOLD)Job Finder - Development Commands$(RESET)"
	@echo ""
	@echo "$(YELLOW)💡 NEW: Use dev-monitor Scripts Panel for better experience!$(RESET)"
	@echo "   Start dev-monitor: cd ../dev-monitor && make dev"
	@echo "   Access UI: http://localhost:5174"
	@echo ""
	@echo "$(CYAN)SETUP & INSTALLATION$(RESET)"
	@echo "  $(GREEN)make setup$(RESET)              Create virtual environment and install all dependencies"
	@echo "  $(GREEN)make install$(RESET)            Install production dependencies only"
	@echo "  $(GREEN)make dev-install$(RESET)        Install development dependencies"
	@echo ""
	@echo "$(CYAN)RUNNING THE APPLICATION$(RESET)"
	@echo "  $(GREEN)make run$(RESET)                Run full job search pipeline (scrape + AI matching)"
	@echo "  $(GREEN)make search$(RESET)             Run basic search without AI matching"
	@echo "  $(GREEN)make worker$(RESET)             Start queue worker for processing jobs"
	@echo "  $(GREEN)make scheduler$(RESET)          Start job scheduler for automated searches"
	@echo ""
	@echo "$(CYAN)TESTING$(RESET)"
	@echo "  $(GREEN)make test$(RESET)               Run all tests"
	@echo "  $(GREEN)make test-coverage$(RESET)      Run tests with coverage report"
	@echo "  $(GREEN)make test-e2e$(RESET)           Fast E2E test: 1 job/type, validate decision tree (90-120s)"
	@echo "  $(GREEN)make test-e2e-full$(RESET)      Full E2E test: all prod data, quality assessment (monitors until complete)"
	@echo "  $(GREEN)make test-e2e-local$(RESET)     Local E2E test: Uses Firebase emulators (no staging/prod data)"
	@echo "  $(GREEN)make test-e2e-local-verbose$(RESET)  Local E2E test with verbose logging"
	@echo "  $(GREEN)make test-e2e-local-full$(RESET)  Full local E2E test (20+ jobs with emulators)"
	@echo "  $(GREEN)make test-specific$(RESET) TEST=<name>  Run specific test file"
	@echo "  $(GREEN)make smoke-queue$(RESET)        Run queue pipeline smoke test (validates full pipeline)"
	@echo ""
	@echo "$(CYAN)CODE QUALITY$(RESET)"
	@echo "  $(GREEN)make lint$(RESET)               Run code linter (flake8)"
	@echo "  $(GREEN)make format$(RESET)             Format code with black"
	@echo "  $(GREEN)make format-check$(RESET)       Check formatting without changes"
	@echo "  $(GREEN)make type-check$(RESET)         Run type checking with mypy"
	@echo "  $(GREEN)make quality$(RESET)            Run all quality checks (lint + format-check + type-check)"
	@echo ""
	@echo "$(CYAN)DOCKER OPERATIONS$(RESET)"
	@echo "  $(GREEN)make docker-build$(RESET)       Build Docker image"
	@echo "  $(GREEN)make docker-push$(RESET)        Push image to registry"
	@echo "  $(GREEN)make docker-run$(RESET)         Run container locally"
	@echo "  $(GREEN)make docker-up$(RESET)          Start development services (requires emulators)"
	@echo "  $(GREEN)make docker-down$(RESET)        Stop docker-compose services"
	@echo "  $(GREEN)make docker-logs$(RESET)        View docker-compose logs"
	@echo "  $(GREEN)make docker-dev$(RESET)         Build and run development environment"
	@echo "  $(GREEN)make docker-dev-shell$(RESET)   Enter development container shell"
	@echo ""
	@echo "$(CYAN)DATABASE UTILITIES$(RESET)"
	@echo "  $(GREEN)make db-explore$(RESET)         Explore Firestore collections"
	@echo "  $(GREEN)make db-cleanup$(RESET)         Clean up Firestore data"
	@echo "  $(GREEN)make db-merge-companies$(RESET) Merge duplicate company records"
	@echo "  $(GREEN)make db-setup-listings$(RESET)  Setup job listings in database"
	@echo "  $(GREEN)make db-setup-config$(RESET)    Setup Firestore configuration (safe - only creates if missing)"
	@echo ""
	@echo "$(CYAN)DEPLOYMENT$(RESET)"
	@echo "  $(GREEN)make deploy-staging$(RESET)     Deploy to staging environment"
	@echo "  $(GREEN)make deploy-production$(RESET)  Deploy to production environment"
	@echo ""
	@echo "$(CYAN)CLEANUP$(RESET)"
	@echo "  $(GREEN)make clean$(RESET)              Remove Python cache files"
	@echo "  $(GREEN)make clean-cache$(RESET)        Remove all cache directories"
	@echo "  $(GREEN)make clean-all$(RESET)          Remove cache, venv, and build artifacts"
	@echo ""
	@echo "$(YELLOW)Configuration:$(RESET)"
	@echo "  - Config file: config/config.yaml"
	@echo "  - Environment: $(ENV_FILE)"
	@echo "  - Profile: data/profile.json (or Firestore)"

## === Setup & Installation ===

setup: ## Create virtual environment and install all dependencies
	@echo "$(CYAN)Setting up development environment...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV_DIR); \
	fi
	@echo "Installing dependencies..."
	@. $(VENV_DIR)/bin/activate && $(PIP) install --upgrade pip
	@. $(VENV_DIR)/bin/activate && $(PIP) install -e ".[dev]"
	@echo "$(GREEN)✓ Setup complete! Activate with: source $(VENV_DIR)/bin/activate$(RESET)"

install: ## Install production dependencies only
	@echo "$(CYAN)Installing production dependencies...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PIP) install -e .
	@echo "$(GREEN)✓ Production dependencies installed$(RESET)"

dev-install: ## Install development dependencies
	@echo "$(CYAN)Installing development dependencies...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PIP) install -e ".[dev]"
	@echo "$(GREEN)✓ Development dependencies installed$(RESET)"

## === Running the Application ===

run: ## Run full job search pipeline (scrape + AI matching)
	@echo "$(CYAN)Running job search pipeline...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) run_job_search.py

search: ## Run basic search without AI matching
	@echo "$(CYAN)Running basic job search...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) run_search.py

worker: ## Start queue worker for processing jobs
	@echo "$(CYAN)Starting queue worker...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) $(SCRIPTS_DIR)/workers/queue_worker.py

scheduler: ## Start job scheduler for automated searches
	@echo "$(CYAN)Starting job scheduler...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) $(SCRIPTS_DIR)/workers/scheduler.py

## === Testing ===

test: ## Run all tests
	@echo "$(YELLOW)💡 Tip: Use dev-monitor Scripts Panel: http://localhost:5174 → Test Worker$(RESET)"
	@echo "$(CYAN)Running tests...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTEST) $(TEST_DIR) -v

test-coverage: ## Run tests with coverage report
	@echo "$(CYAN)Running tests with coverage...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTEST) $(TEST_DIR) --cov=$(SRC_DIR)/job_finder --cov-report=html --cov-report=term

test-e2e: ## Run fast E2E test - submits jobs sequentially, monitors each until complete (90-120s per job)
	@echo "$(CYAN)Running fast E2E test (sequential job submission)...$(RESET)"
	@echo "$(GREEN)✓ Safe: Testing on portfolio-staging (not production)$(RESET)"
	@echo "$(BLUE)ℹ️  Strategy: Submit job → monitor until complete → submit next job$(RESET)"
	@echo "$(CYAN)Purpose: Validate state-driven pipeline and loop prevention$(RESET)"
	@sleep 1
	@mkdir -p test_results
	@export TEST_RUN_ID="e2e_quick_$$(date +%s)" && \
	export RESULTS_DIR="test_results/$${TEST_RUN_ID}" && \
	export GOOGLE_APPLICATION_CREDENTIALS="$(shell pwd)/credentials/serviceAccountKey.json" && \
	mkdir -p "$${RESULTS_DIR}" && \
	echo "$(BLUE)Test Run ID: $${TEST_RUN_ID}$(RESET)" && \
	echo "$(BLUE)Test Database: portfolio-staging$(RESET)" && \
	echo "$(BLUE)Source Database: portfolio (production - read only)$(RESET)" && \
	echo "$(BLUE)Results Directory: $${RESULTS_DIR}$(RESET)" && \
	echo "" && \
	echo "$(CYAN)[1/2] Sequential job submission with monitoring...$(RESET)" && \
	. $(VENV_DIR)/bin/activate && $(PYTHON) tests/e2e/data_collector.py \
		--database portfolio-staging \
		--source-database portfolio \
		--output-dir "$${RESULTS_DIR}" \
		--test-count 2 \
		--test-mode decision-tree \
		--verbose && \
	echo "" && \
	echo "$(CYAN)[2/2] Validating decision tree results...$(RESET)" && \
	. $(VENV_DIR)/bin/activate && $(PYTHON) tests/e2e/validate_decision_tree.py \
		--database portfolio-staging \
		--results-dir "$${RESULTS_DIR}" && \
	echo "" && \
	echo "$(GREEN)✓ Fast E2E Test Complete!$(RESET)" && \
	echo "$(YELLOW)Results: $${RESULTS_DIR}$(RESET)"

test-e2e-full: ## Run complete E2E suite with ALL production data for quality assessment (monitors until complete)
	@echo "$(CYAN)Starting FULL E2E test suite (quality assessment)...$(RESET)"
	@echo "$(YELLOW)⚠️  WARNING: This will CLEAR collections in portfolio-staging database$(RESET)"
	@echo "$(GREEN)✓ Safe: Testing on portfolio-staging (not production)$(RESET)"
	@echo "$(BLUE)ℹ️  This will process ALL production data through the pipeline$(RESET)"
	@echo "$(CYAN)Purpose: Data quality validation, comprehensive system test$(RESET)"
	@sleep 2
	@mkdir -p test_results
	@export TEST_RUN_ID="e2e_full_$$(date +%s)" && \
	export RESULTS_DIR="test_results/$${TEST_RUN_ID}" && \
	export GOOGLE_APPLICATION_CREDENTIALS="$(shell pwd)/credentials/serviceAccountKey.json" && \
	mkdir -p "$${RESULTS_DIR}" && \
	echo "$(BLUE)Test Run ID: $${TEST_RUN_ID}$(RESET)" && \
	echo "$(BLUE)Test Database: portfolio-staging (staging)$(RESET)" && \
	echo "$(BLUE)Source Database: portfolio (production - read only)$(RESET)" && \
	echo "$(BLUE)Results Directory: $${RESULTS_DIR}$(RESET)" && \
	echo "" && \
	echo "$(CYAN)[1/5] Seeding staging with ALL production data...$(RESET)" && \
	. $(VENV_DIR)/bin/activate && $(PYTHON) tests/e2e/data_collector.py \
		--database portfolio-staging \
		--source-database portfolio \
		--output-dir "$${RESULTS_DIR}" \
		--backup-dir "$${RESULTS_DIR}/backup" \
		--clean-before \
		--test-mode full \
		--verbose && \
	echo "" && \
	echo "$(CYAN)[2/5] Monitoring queue until all jobs complete...$(RESET)" && \
	. $(VENV_DIR)/bin/activate && $(PYTHON) tests/e2e/queue_monitor.py \
		--database portfolio-staging \
		--timeout 3600 \
		--stream-logs \
		--output "$${RESULTS_DIR}/monitor.log" && \
	echo "" && \
	echo "$(CYAN)[3/5] Analyzing results and quality metrics...$(RESET)" && \
	. $(VENV_DIR)/bin/activate && $(PYTHON) tests/e2e/results_analyzer.py \
		--results-dir "$${RESULTS_DIR}" \
		--output-dir "$${RESULTS_DIR}/analysis" \
		--verbose && \
	echo "" && \
	echo "$(CYAN)[4/5] Generating data quality report...$(RESET)" && \
	. $(VENV_DIR)/bin/activate && $(PYTHON) tests/e2e/quality_report.py \
		--database portfolio-staging \
		--results-dir "$${RESULTS_DIR}" \
		--output "$${RESULTS_DIR}/quality_report.html" && \
	echo "" && \
	echo "$(CYAN)[5/5] Saving comprehensive results...$(RESET)" && \
	. $(VENV_DIR)/bin/activate && $(PYTHON) -c "import json; import sys; sys.path.insert(0, 'tests'); from e2e.data_collector import TestRunResult; print('Results saved')" && \
	echo "" && \
	echo "$(GREEN)✓ Full E2E Test Suite Complete!$(RESET)" && \
	echo "$(YELLOW)Results saved to: $${RESULTS_DIR}$(RESET)" && \
	echo "$(YELLOW)Quality report: $${RESULTS_DIR}/quality_report.html$(RESET)"

test-e2e-local: ## Run local E2E test with Firebase emulators (fast mode, Docker)
	@echo "$(CYAN)Running local E2E test with Firebase emulators...$(RESET)"
	@echo "$(GREEN)✓ Safe: Uses Firebase emulators (no staging/prod data)$(RESET)"
	@echo "$(BLUE)ℹ️  Prerequisites: Portfolio emulators must be running$(RESET)"
	@echo "$(CYAN)Start emulators: cd ~/path/to/portfolio && make firebase-emulators$(RESET)"
	@sleep 1
	@. $(VENV_DIR)/bin/activate && $(PYTHON) tests/e2e/run_local_e2e.py

test-e2e-local-verbose: ## Run local E2E test with verbose logging
	@echo "$(CYAN)Running local E2E test with verbose logging...$(RESET)"
	@echo "$(GREEN)✓ Safe: Uses Firebase emulators (no staging/prod data)$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) tests/e2e/run_local_e2e.py --verbose

test-e2e-local-full: ## Run full local E2E test (20+ jobs with emulators)
	@echo "$(CYAN)Running FULL local E2E test with Firebase emulators...$(RESET)"
	@echo "$(GREEN)✓ Safe: Uses Firebase emulators (no staging/prod data)$(RESET)"
	@echo "$(YELLOW)⚠️  This will take longer (20+ jobs)$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) tests/e2e/run_local_e2e.py --full

test-e2e-local-no-docker: ## Run local E2E test without Docker (direct Python)
	@echo "$(CYAN)Running local E2E test without Docker...$(RESET)"
	@echo "$(GREEN)✓ Safe: Uses Firebase emulators (no staging/prod data)$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) tests/e2e/run_local_e2e.py --no-docker

test-specific: ## Run specific test file (use TEST=filename)
	@if [ -z "$(TEST)" ]; then \
		echo "$(YELLOW)Usage: make test-specific TEST=test_filters.py$(RESET)"; \
		exit 1; \
	fi
	@echo "$(CYAN)Running test: $(TEST)$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTEST) $(TEST_DIR)/$(TEST) -v

smoke-queue: ## Run queue pipeline smoke test
	@echo "$(CYAN)Running queue pipeline smoke test...$(RESET)"
	@echo "$(GREEN)✓ Safe: Testing on portfolio-staging (not production)$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) $(SCRIPTS_DIR)/smoke/queue_pipeline_smoke.py --env staging
	@echo "$(GREEN)✓ Smoke test complete. Check test_results/ for reports.$(RESET)"

## === Code Quality ===

lint: ## Run code linter (flake8)
	@echo "$(YELLOW)💡 Tip: Use dev-monitor Scripts Panel: http://localhost:5174 → Lint Worker$(RESET)"
	@echo "$(CYAN)Running linter...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(FLAKE8) $(SRC_DIR) $(TEST_DIR)
	@echo "$(GREEN)✓ Linting passed$(RESET)"

format: ## Format code with black
	@echo "$(YELLOW)💡 Tip: Use dev-monitor Scripts Panel: http://localhost:5174 → Format Worker$(RESET)"
	@echo "$(CYAN)Formatting code...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(BLACK) $(SRC_DIR) $(TEST_DIR) $(SCRIPTS_DIR) *.py
	@echo "$(GREEN)✓ Code formatted$(RESET)"

format-check: ## Check formatting without changes
	@echo "$(YELLOW)💡 Tip: Use dev-monitor Scripts Panel: http://localhost:5174 → Lint Worker$(RESET)"
	@echo "$(CYAN)Checking code formatting...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(BLACK) --check $(SRC_DIR) $(TEST_DIR) $(SCRIPTS_DIR) *.py
	@echo "$(GREEN)✓ Formatting check passed$(RESET)"

type-check: ## Run type checking with mypy
	@echo "$(CYAN)Running type checker...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(MYPY) $(SRC_DIR)
	@echo "$(GREEN)✓ Type checking passed$(RESET)"

quality: format-check lint type-check ## Run all quality checks
	@echo "$(GREEN)✓ All quality checks passed$(RESET)"

## === Docker Operations ===

docker-build: ## Build Docker image
	@echo "$(CYAN)Building Docker image...$(RESET)"
	$(DOCKER) build -t $(DOCKER_IMAGE):latest .
	@echo "$(GREEN)✓ Docker image built$(RESET)"

docker-push: ## Push image to registry
	@echo "$(CYAN)Pushing Docker image to registry...$(RESET)"
	$(DOCKER) tag $(DOCKER_IMAGE):latest $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):latest
	$(DOCKER) push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):latest
	@echo "$(GREEN)✓ Image pushed to registry$(RESET)"

docker-run: ## Run container locally
	@echo "$(CYAN)Running Docker container...$(RESET)"
	$(DOCKER) run --rm --env-file $(ENV_FILE) $(DOCKER_IMAGE):latest

docker-up: ## Start docker-compose development services
	@echo "$(CYAN)Starting Docker Compose development services...$(RESET)"
	@echo "$(YELLOW)Prerequisites: Firebase emulators must be running in job-finder-BE$(RESET)"
	$(DOCKER_COMPOSE) -f docker-compose.dev.yml up
	@echo "$(GREEN)✓ Development services started$(RESET)"

docker-down: ## Stop docker-compose services
	@echo "$(CYAN)Stopping Docker Compose services...$(RESET)"
	$(DOCKER_COMPOSE) -f docker-compose.dev.yml down
	@echo "$(GREEN)✓ Services stopped$(RESET)"

docker-logs: ## View docker-compose logs
	$(DOCKER_COMPOSE) -f docker-compose.dev.yml logs -f
## === Standard Development Aliases (for consistency with other repos) ===

dev: docker-dev ## Alias for docker-dev (standard target)

dev-stop: docker-down ## Alias for docker-down (standard target)

dev-status: ## Check if worker Docker container is running
	@echo "$(CYAN)Checking worker Docker container status...$(RESET)"
	@if docker ps --filter "name=job-finder" --filter "status=running" | grep -q "job-finder"; then \
		echo "$(GREEN)✓ Worker container is running$(RESET)"; \
		docker ps --filter "name=job-finder" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"; \
	else \
		echo "$(YELLOW)⚠ Worker container is not running$(RESET)"; \
		echo "  Start with: make dev"; \
	fi

dev-logs: docker-logs ## Alias for docker-logs (standard target)

## === Docker Development ===

docker-dev: ## Build and run development environment
	@echo "$(CYAN)Building and running development environment...$(RESET)"
	@echo "$(YELLOW)Prerequisites:$(RESET)"
	@echo "  1. Firebase emulators running in job-finder-BE"
	@echo "  2. Emulators at localhost:8080 (Firestore) and localhost:9099 (Auth)"
	@echo ""
	$(DOCKER_COMPOSE) -f docker-compose.dev.yml up --build

docker-dev-shell: ## Enter development container shell
	@echo "$(CYAN)Entering development container shell...$(RESET)"
	$(DOCKER_COMPOSE) -f docker-compose.dev.yml exec job-finder bash

## === Database Utilities ===

db-explore: ## Explore Firestore collections
	@echo "$(CYAN)Exploring Firestore database...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) $(SCRIPTS_DIR)/database/explore_firestore.py

db-cleanup: ## Clean up Firestore data
	@echo "$(CYAN)Cleaning up Firestore...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) $(SCRIPTS_DIR)/database/cleanup_firestore.py

db-merge-companies: ## Merge duplicate company records
	@echo "$(CYAN)Merging duplicate companies...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) $(SCRIPTS_DIR)/database/merge_company_duplicates.py

db-setup-listings: ## Setup job listings in database
	@echo "$(CYAN)Setting up job listings...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) $(SCRIPTS_DIR)/database/setup_job_listings.py

db-cleanup-matches: ## Clean up job matches
	@echo "$(CYAN)Cleaning up job matches...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) $(SCRIPTS_DIR)/database/cleanup_job_matches.py

db-setup-config: ## Setup Firestore configuration (only creates if missing)
	@echo "$(CYAN)Setting up Firestore configuration...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) $(SCRIPTS_DIR)/setup_firestore_config.py

## === Deployment ===

deploy-staging: docker-build ## Deploy to staging environment
	@echo "$(CYAN)Deploying to staging...$(RESET)"
	@echo "$(YELLOW)Note: Ensure you're logged into the container registry$(RESET)"
	$(DOCKER) tag $(DOCKER_IMAGE):latest $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):staging
	$(DOCKER) push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):staging
	@echo "$(GREEN)✓ Deployed to staging$(RESET)"
	@echo "$(YELLOW)Remember to update the staging server to pull the new image$(RESET)"

deploy-production: ## Deploy to production environment
	@echo "$(CYAN)Deploying to production...$(RESET)"
	@echo "$(YELLOW)⚠️  Production deployment - are you sure? (Ctrl+C to cancel)$(RESET)"
	@sleep 3
	@echo "$(YELLOW)Note: Ensure you're logged into the container registry$(RESET)"
	$(DOCKER) tag $(DOCKER_IMAGE):latest $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):production
	$(DOCKER) push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):production
	@echo "$(GREEN)✓ Deployed to production$(RESET)"
	@echo "$(YELLOW)Remember to update the production server to pull the new image$(RESET)"

## === Profile Management ===

create-profile: ## Create a new profile template
	@echo "$(CYAN)Creating profile template...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) -m job_finder.main --create-profile data/profile.json
	@echo "$(GREEN)✓ Profile template created at data/profile.json$(RESET)"
	@echo "$(YELLOW)Edit the profile and update config/config.yaml to use it$(RESET)"

## === Utility Scripts ===

score-companies: ## Score and tier companies for rotation
	@echo "$(CYAN)Scoring companies...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) $(SCRIPTS_DIR)/score_companies.py

add-companies: ## Add phase 1 companies to database
	@echo "$(CYAN)Adding companies to database...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) $(SCRIPTS_DIR)/add_phase1_companies.py

test-pipeline: ## Test the processing pipeline
	@echo "$(CYAN)Testing pipeline...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) $(SCRIPTS_DIR)/test_pipeline.py

migrate-listings: ## Migrate listings to new sources structure
	@echo "$(CYAN)Migrating listings...$(RESET)"
	@. $(VENV_DIR)/bin/activate && $(PYTHON) $(SCRIPTS_DIR)/migrate_listings_to_sources.py

## === Cleanup ===

clean: ## Remove Python cache files
	@echo "$(CYAN)Cleaning Python cache...$(RESET)"
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Python cache cleaned$(RESET)"

clean-cache: clean ## Remove all cache directories
	@echo "$(CYAN)Cleaning all cache...$(RESET)"
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage
	@echo "$(GREEN)✓ Cache directories cleaned$(RESET)"

clean-all: clean-cache ## Remove cache, venv, and build artifacts
	@echo "$(CYAN)Cleaning everything...$(RESET)"
	rm -rf $(VENV_DIR)
	rm -rf build dist *.egg-info
	rm -rf logs/*
	@echo "$(GREEN)✓ All artifacts cleaned$(RESET)"
	@echo "$(YELLOW)Run 'make setup' to reinstall$(RESET)"

## === Development Shortcuts ===

quick-test: ## Run quick tests without coverage
	@. $(VENV_DIR)/bin/activate && $(PYTEST) $(TEST_DIR) -x --tb=short

watch-test: ## Run tests in watch mode (requires pytest-watch)
	@. $(VENV_DIR)/bin/activate && $(PYTHON) -m pytest_watch $(TEST_DIR) -v

## === Environment Management ===

check-env: ## Check if required environment variables are set
	@echo "$(CYAN)Checking environment variables...$(RESET)"
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "$(YELLOW)⚠️  No .env file found. Copy .env.example to .env and configure it.$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Environment file found$(RESET)"
	@grep -E '^[A-Z_]+=' $(ENV_FILE) | cut -d= -f1 | while read var; do \
		echo "  $$var: configured"; \
	done

show-config: ## Display current configuration
	@echo "$(CYAN)Current Configuration:$(RESET)"
	@if [ -f "config/config.yaml" ]; then \
		head -30 config/config.yaml; \
		echo "\n$(YELLOW)... (truncated, see full file at config/config.yaml)$(RESET)"; \
	else \
		echo "$(YELLOW)No config file found at config/config.yaml$(RESET)"; \
	fi

## === Git Hooks (if using pre-commit) ===

install-hooks: ## Install git pre-commit hooks
	@echo "$(CYAN)Installing git hooks...$(RESET)"
	@. $(VENV_DIR)/bin/activate && pre-commit install
	@echo "$(GREEN)✓ Git hooks installed$(RESET)"

run-hooks: ## Run pre-commit hooks on all files
	@echo "$(CYAN)Running pre-commit hooks...$(RESET)"
	@. $(VENV_DIR)/bin/activate && pre-commit run --all-files
