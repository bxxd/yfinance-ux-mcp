.PHONY: help test lint lint-fix mypy ruff serve clean all

# Default target - show help
help:
	@echo "yfinance-mcp development commands:"
	@echo ""
	@echo "  make test       - Run all tests"
	@echo "  make lint       - Run type checking (mypy) and linting (ruff)"
	@echo "  make lint-fix   - Auto-fix linting issues where possible"
	@echo "  make mypy       - Run mypy type checking only"
	@echo "  make ruff       - Run ruff linting only"
	@echo "  make serve      - Run MCP server (stdio mode for Claude Code)"
	@echo "  make clean      - Remove Python cache files"
	@echo "  make all        - Run lint + test (use before committing)"
	@echo ""
	@echo "Before committing, ALWAYS run: make all"

# Run all tests
test:
	@echo "Running tests..."
	@poetry run python tests/test_core.py

# Run type checking only
mypy:
	@echo "Running mypy type checker..."
	@poetry run mypy yfmcp/

# Run linting only
ruff:
	@echo "Running ruff linter..."
	@poetry run ruff check yfmcp/

# Run both type checking and linting
lint: mypy ruff
	@echo "✓ All checks passed!"

# Auto-fix linting issues and run checks
lint-fix:
	@echo "Auto-fixing linting issues..."
	@poetry run ruff check --fix yfmcp/
	@echo ""
	@$(MAKE) lint

# Run MCP server via stdio (for Claude Code)
serve:
	@echo "Starting MCP server (stdio mode)..." >&2
	@echo "Press Ctrl+C to stop" >&2
	@poetry run python -m yfmcp.server

# Clean Python cache files
clean:
	@echo "Cleaning Python cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned"

# Run everything (use before committing)
all: lint test
	@echo ""
	@echo "✓ All checks passed - ready to commit!"
