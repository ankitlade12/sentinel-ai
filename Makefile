.PHONY: help setup test lint format dev-backend dev-frontend types demo index clean \
        docker-build docker-up docker-down docker-logs docker-push

BACKEND_IMAGE  ?= sentinel-backend
FRONTEND_IMAGE ?= sentinel-frontend
TAG            ?= latest
# Set REGISTRY to your Artifact Registry / Docker Hub prefix, e.g.:
#   REGISTRY=us-central1-docker.pkg.dev/PROJECT/sentinel make docker-push
REGISTRY       ?=

help:
	@echo "Sentinel — Make targets"
	@echo ""
	@echo "  make setup          Create venv and install deps (uv sync --extra dev)"
	@echo "  make index          Build / refresh the trusted-corpus vector index"
	@echo "  make demo           Run the end-to-end demo scenarios through Sentinel"
	@echo "  make test           Run pytest"
	@echo "  make lint           ruff check + ruff format --check + mypy"
	@echo "  make format         Auto-fix lint issues and format code"
	@echo "  make dev-backend    Run FastAPI dev server (SSE)"
	@echo "  make dev-frontend   Run the Next.js dashboard"
	@echo "  make types          Generate TypeScript types from Pydantic models"
	@echo "  make clean          Remove caches, venv, build artifacts"
	@echo ""
	@echo "  make docker-build   Build backend + frontend images"
	@echo "  make docker-up      Start all services via docker-compose"
	@echo "  make docker-down    Stop and remove all services"
	@echo "  make docker-logs    Tail logs for all services"
	@echo "  make docker-push    Tag and push images to \$$REGISTRY"

setup:
	uv sync --extra dev

index:
	uv run python scripts/index_corpus.py

demo:
	uv run python scripts/eval_scenarios.py

test:
	uv run pytest

lint:
	uv run ruff check backend/ scripts/
	uv run ruff format --check backend/ scripts/
	uv run mypy backend/

format:
	uv run ruff check --fix backend/ scripts/
	uv run ruff format backend/ scripts/

dev-backend:
	uv run uvicorn backend.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

types:
	uv run python scripts/generate_typescript_types.py

clean:
	rm -rf .venv/ dist/ build/ .pytest_cache/ .ruff_cache/ .mypy_cache/
	find backend scripts -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	cd frontend 2>/dev/null && rm -rf node_modules .next || true

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build:
	docker build -f backend/Dockerfile --tag $(BACKEND_IMAGE):$(TAG) .
	docker build -f frontend/Dockerfile --tag $(FRONTEND_IMAGE):$(TAG) frontend

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-push:
	@if [ -z "$(REGISTRY)" ]; then echo "Set REGISTRY= to your Artifact Registry / Docker Hub prefix"; exit 1; fi
	docker tag $(BACKEND_IMAGE):$(TAG)  $(REGISTRY)/$(BACKEND_IMAGE):$(TAG)
	docker tag $(FRONTEND_IMAGE):$(TAG) $(REGISTRY)/$(FRONTEND_IMAGE):$(TAG)
	docker push $(REGISTRY)/$(BACKEND_IMAGE):$(TAG)
	docker push $(REGISTRY)/$(FRONTEND_IMAGE):$(TAG)
