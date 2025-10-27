# Job Finder Worker Makefile
.PHONY: help install dev prod test coverage lint clean health status shutdown

PYTHON := python3
VENV_DIR := venv
WORKER_PORT := 5555

CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
RESET := \033[0m

.DEFAULT_GOAL := help

help: ## Show available commands
	@echo "$(CYAN)Job Finder Worker - Flask Application$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(CYAN)%-15s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Setup and Installation
install: ## Install dependencies in virtual environment
	@echo "$(CYAN)Installing dependencies...$(RESET)"
	@if [ ! -d "$(VENV_DIR)" ]; then \
		$(PYTHON) -m venv $(VENV_DIR); \
	fi
	@. $(VENV_DIR)/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(RESET)"

install-dev: ## Install development dependencies
	@echo "$(CYAN)Installing development dependencies...$(RESET)"
	@. $(VENV_DIR)/bin/activate && pip install -r requirements.txt -r requirements-test.txt
	@echo "$(GREEN)✓ Development dependencies installed$(RESET)"

# Running the Worker
dev: ## Start worker in development mode
	@echo "$(GREEN)Starting Flask worker (development mode)...$(RESET)"
	@./run_dev.sh

prod: ## Start worker in production mode
	@echo "$(GREEN)Starting Flask worker (production mode)...$(RESET)"
	@./run_prod.sh

start: dev ## Alias for 'make dev'

# Testing
test: ## Run all tests
	@echo "$(CYAN)Running tests...$(RESET)"
	@. $(VENV_DIR)/bin/activate && pytest -v

test-fast: ## Run tests without coverage
	@echo "$(CYAN)Running fast tests...$(RESET)"
	@. $(VENV_DIR)/bin/activate && pytest -v --no-cov

coverage: ## Run tests with coverage report
	@echo "$(CYAN)Running tests with coverage...$(RESET)"
	@. $(VENV_DIR)/bin/activate && pytest --cov=src/job_finder --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode
	@echo "$(CYAN)Running tests in watch mode...$(RESET)"
	@. $(VENV_DIR)/bin/activate && pytest-watch

# Code Quality
lint: ## Run linter (flake8)
	@echo "$(CYAN)Running linter...$(RESET)"
	@. $(VENV_DIR)/bin/activate && flake8 src tests --max-line-length=100 --ignore=E203,W503

format: ## Format code with black
	@echo "$(CYAN)Formatting code...$(RESET)"
	@. $(VENV_DIR)/bin/activate && black src tests

type-check: ## Run type checker (mypy)
	@echo "$(CYAN)Running type checker...$(RESET)"
	@. $(VENV_DIR)/bin/activate && mypy src

# Worker Control
health: ## Check worker health
	@echo "$(CYAN)Checking worker health...$(RESET)"
	@curl -s "http://localhost:$(WORKER_PORT)/health" | jq . || echo "$(RED)Worker not responding$(RESET)"

status: ## Get worker status
	@echo "$(CYAN)Getting worker status...$(RESET)"
	@curl -s "http://localhost:$(WORKER_PORT)/status" | jq . || echo "$(RED)Worker not responding$(RESET)"

shutdown: ## Gracefully shutdown worker
	@echo "$(YELLOW)Shutting down worker...$(RESET)"
	@curl -X POST "http://localhost:$(WORKER_PORT)/shutdown" || echo "$(RED)Worker not responding$(RESET)"

# Logs
logs: ## Tail worker logs
	@tail -f logs/worker.log

logs-json: ## Tail worker logs with JSON formatting
	@tail -f logs/worker.log | jq '.'

logs-errors: ## Show only error logs
	@grep "ERROR" logs/worker.log | tail -n 50

# Cleanup
clean: ## Clean up generated files
	@echo "$(CYAN)Cleaning up...$(RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@rm -rf htmlcov .pytest_cache .mypy_cache 2>/dev/null || true
	@echo "$(GREEN)✓ Cleaned up$(RESET)"

clean-logs: ## Clean log files
	@echo "$(YELLOW)Cleaning logs...$(RESET)"
	@rm -f logs/*.log
	@echo "$(GREEN)✓ Logs cleaned$(RESET)"

clean-all: clean clean-logs ## Clean everything including venv
	@echo "$(RED)Removing virtual environment...$(RESET)"
	@rm -rf $(VENV_DIR)
	@echo "$(GREEN)✓ Everything cleaned$(RESET)"

# Development Utilities
shell: ## Start Python shell with app context
	@echo "$(CYAN)Starting Python shell...$(RESET)"
	@. $(VENV_DIR)/bin/activate && python3

check-config: ## Validate configuration files
	@echo "$(CYAN)Checking configuration...$(RESET)"
	@. $(VENV_DIR)/bin/activate && python3 -c "import yaml; yaml.safe_load(open('config/config.dev.yaml'))"
	@echo "$(GREEN)✓ Configuration valid$(RESET)"

check-env: ## Check environment variables
	@echo "$(CYAN)Checking environment...$(RESET)"
	@echo "GOOGLE_APPLICATION_CREDENTIALS: $$GOOGLE_APPLICATION_CREDENTIALS"
	@echo "ANTHROPIC_API_KEY: $$([ -n "$$ANTHROPIC_API_KEY" ] && echo 'Set' || echo 'Not set')"
	@echo "OPENAI_API_KEY: $$([ -n "$$OPENAI_API_KEY" ] && echo 'Set' || echo 'Not set')"

# Documentation
docs: ## View documentation
	@echo "$(CYAN)Available documentation:$(RESET)"
	@echo "  - README.md - General overview"
	@echo "  - FLASK_DEPLOYMENT.md - Deployment guide"
	@echo "  - DEPLOYMENT.md - Legacy deployment info"
	@echo "  - TEST_IMPROVEMENTS_FINAL_REPORT.md - Test coverage report"
