.RECIPEPREFIX = >
.PHONY: setup up down logs migrate seed test lint format check-notebooks

setup:
> python -m venv .venv && . .venv/bin/activate && pip install -e ".[analytics,dev]" && pre-commit install

up:
> docker compose up -d

down:
> docker compose down

logs:
> docker compose logs -f

migrate:
> alembic upgrade head

check-notebooks:
> ! grep -rlE "(from fundapp|import fundapp)" notebooks/ 2>/dev/null

seed:
> python -m fundapp.cli seed

test:
> pytest -q

lint:
> ruff check src tests

format:
> black src tests && ruff check --fix src tests
