.PHONY: help test lint lint-fix mypy ruff stdio server logs clean all

# Default target - show help
help:
	@echo "yfinance-mcp development commands:"
	@echo ""
	@echo "  make test       - Run all tests"
	@echo "  make lint       - Run type checking (mypy) and linting (ruff)"
	@echo "  make lint-fix   - Auto-fix linting issues where possible"
	@echo "  make mypy       - Run mypy type checking only"
	@echo "  make ruff       - Run ruff linting only"
	@echo "  make stdio      - Run MCP server (stdio mode for Claude Code)"
	@echo "  make server     - Run MCP HTTP server (port 5001, logs to logs/server.log)"
	@echo "  make logs       - Tail server logs (logs/server.log)"
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
stdio:
	@echo "Starting MCP server (stdio mode)..." >&2
	@echo "Press Ctrl+C to stop" >&2
	@poetry run python -m yfmcp.server

# Run MCP HTTP server (for web integration)
server:
	@mkdir -p logs
	@echo "Stopping existing server..." >&2
	@-pkill -f "uvicorn.*yfmcp.*server_http" 2>/dev/null
	@sleep 1
	@echo "Starting MCP HTTP server on http://127.0.0.1:5001 (logs/server.log)..." >&2
	@nohup poetry run uvicorn yfmcp.server_http:app --host 127.0.0.1 --port 5001 > logs/server.log 2>&1 &
	@sleep 1
	@echo "Server started (logs/server.log)"

# Tail server logs
logs:
	@tail -f logs/server.log

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
