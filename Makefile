.PHONY: help install dev build test lint format docs docker-up docker-down clean

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies (Node + Python)
	npm install
	pip install -r requirements.txt

dev: ## Run frontend and backend in development mode
	npm run dev & \
	python -m services.core.main; \
	wait

build: ## Build frontend for production
	npm run build

test: ## Run all tests
	-npm test
	pytest tests/ -v

lint: ## Lint and format-check all code
	npx prettier --check .
	-ruff check services/ tests/

format: ## Auto-format all code
	npx prettier --write .
	-ruff format services/ tests/

docs: ## Serve documentation locally
	mkdocs serve

docs-build: ## Build documentation site
	mkdocs build

docker-up: ## Start all services with Docker Compose
	docker compose up -d --build

docker-down: ## Stop all Docker services
	docker compose down

clean: ## Remove build artifacts and caches
	rm -rf dist build site node_modules/.vite
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache
