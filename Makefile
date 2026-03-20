.PHONY: test lint deploy

test:
	venv/bin/python -m pytest tests/ -q

lint:
	venv/bin/ruff check . && venv/bin/ruff format --check . && echo "lint and format clean"

deploy:
	bash scripts/deploy-skill.sh
