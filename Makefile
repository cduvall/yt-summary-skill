.PHONY: test lint

test:
	venv/bin/python -m pytest tests/ -q

lint:
	venv/bin/ruff check . && venv/bin/ruff format --check . && echo "lint and format clean"
