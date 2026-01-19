# Just commands for AAQ-backend (uses uv)

set shell := ["bash", "-c"]

# Create or update the virtualenv and install deps
install:
	uv venv
	. .venv/bin/activate && uv pip install -e ".[dev]"

# Format and lint
ruff:
	uv run ruff check .

# Run pytest suite
TEST_ARGS := ""
test:
	uv run pytest {{TEST_ARGS}}

test-all:
	uv run pytest

# Pre-commit hooks (run them all)
check:
	uv run pre-commit run --all-files

# Start dev server
run:
	uv run uvicorn app.main:app --reload

# Clean cached test artifacts
clean:
	rm -rf .pytest_cache .ruff_cache
