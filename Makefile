.PHONY: up down logs ps test migrate lint type-check fmt build clean

COMPOSE := docker compose

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

build:
	$(COMPOSE) build

test:
	cd backend && uv run pytest
	$(COMPOSE) --profile test run --rm backend-tests
	cd frontend && npm test --if-present

migrate:
	$(COMPOSE) exec backend alembic upgrade head

lint:
	cd backend && uv run ruff format --check . && uv run ruff check .
	cd frontend && npm run lint

type-check:
	cd backend && uv run pyright
	cd frontend && npm run type-check

fmt:
	cd backend && uv run ruff format .
	cd frontend && npx prettier --write .

clean:
	$(COMPOSE) down -v --remove-orphans
