.PHONY: test lint

test:
	pytest tests/ -q

lint:
	venv/bin/ruff check . && venv/bin/ruff format --check . && echo "lint and format clean"
