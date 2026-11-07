.DEFAULT_GOAL := dev

DEV_COMPOSE = docker compose -p demo-ai --env-file .env -f docker/docker-compose.development.yaml
PROD_COMPOSE = docker compose -p demo-ai --env-file .env.production -f docker/docker-compose.production.yaml
DEV_DATABASE = docker compose -p demo-ai --env-file .env -f docker/docker-compose.database.yaml
DEV_DB_UI = docker compose -p demo-ai --env-file .env -f docker/docker-compose.database.yaml -f docker/docker-compose.db-ui.yaml

.PHONY: help install local dev dev-logs dev-down dev-database dev-db-ui dev-database-down test build run logs down clean

help:
	@echo "Available commands:"
	@echo "  make install  Install dependencies with uv"
	@echo "  make          Run Docker Development (default)"
	@echo "  make dev      Run Docker Development with reload"
	@echo "  make local    Run Development locally without Docker"
	@echo "  make dev-logs Follow Development container logs"
	@echo "  make dev-down Stop the Development container"
	@echo "  make dev-database Start MongoDB and Qdrant"
	@echo "  make dev-db-ui Start MongoDB, Qdrant and Mongo Express"
	@echo "  make test     Run tests"
	@echo "  make build    Build the Production Docker image"
	@echo "  make run      Run Production with Docker"
	@echo "  make logs     Follow container logs"
	@echo "  make down     Stop and remove the container"
	@echo "  make clean    Remove local Python caches"

install:
	uv sync

local:
	uv run python -m app

dev:
	$(DEV_COMPOSE) up --build --force-recreate

dev-logs:
	$(DEV_COMPOSE) logs -f api

dev-down:
	$(DEV_COMPOSE) down

dev-database:
	$(DEV_DATABASE) up -d

dev-db-ui:
	$(DEV_DB_UI) up -d

dev-database-down:
	$(DEV_DATABASE) down

test:
	uv run pytest

build:
	$(PROD_COMPOSE) build

run:
	$(PROD_COMPOSE) up --build -d

logs:
	$(PROD_COMPOSE) logs -f api

down:
	$(PROD_COMPOSE) down

clean:
	uv cache clean
