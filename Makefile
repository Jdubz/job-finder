# Job Finder Worker Makefile
.PHONY: help install start stop test lint flask-start flask-stop flask-test

PYTHON := python3
VENV_DIR := venv
FLASK_PORT := 5555

CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
RESET := \033[0m

.DEFAULT_GOAL := help

help: ## Show available commands
	@echo "$(CYAN)Job Finder Worker$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(CYAN)%-15s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	@if [ ! -d "$(VENV_DIR)" ]; then \
		$(PYTHON) -m venv $(VENV_DIR); \
	fi
	@. $(VENV_DIR)/bin/activate && pip install -r requirements.txt && pip install flask

start: ## Start worker with Docker
	@docker compose -f docker-compose.dev.yml up --build

stop: ## Stop worker
	@docker compose -f docker-compose.dev.yml down

flask-start: ## Start Flask worker (development)
	@echo "$(GREEN)Starting Flask worker on port $(FLASK_PORT)...$(RESET)"
	@. $(VENV_DIR)/bin/activate && python3 src/job_finder/simple_flask_worker.py

flask-stop: ## Stop Flask worker
	@echo "$(YELLOW)Stopping Flask worker...$(RESET)"
	@pkill -f "simple_flask_worker" || echo "$(RED)No Flask worker process found$(RESET)"

flask-test: ## Test Flask worker endpoints
	@echo "$(CYAN)Testing Flask worker endpoints...$(RESET)"
	@. $(VENV_DIR)/bin/activate && python3 test_flask_worker.py

flask-health: ## Check Flask worker health
	@echo "$(CYAN)Checking Flask worker health...$(RESET)"
	@curl -s "http://localhost:$(FLASK_PORT)/health" | jq . || echo "$(RED)Flask worker not responding$(RESET)"

flask-status: ## Get Flask worker status
	@echo "$(CYAN)Getting Flask worker status...$(RESET)"
	@curl -s "http://localhost:$(FLASK_PORT)/status" | jq . || echo "$(RED)Flask worker not responding$(RESET)"

test: ## Run tests
	@. $(VENV_DIR)/bin/activate && pytest

lint: ## Run linter
	@. $(VENV_DIR)/bin/activate && flake8 src tests
