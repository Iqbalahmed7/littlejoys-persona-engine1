#!/bin/bash
# CI pipeline — runs lint, typecheck, security scan, and tests.
# All checks must pass for a PR to be merge-eligible.

set -e

echo "============================================"
echo "  LittleJoys CI Pipeline"
echo "============================================"
echo ""

echo "=== [1/5] Lint ==="
uv run ruff check .
echo "✓ Lint passed"
echo ""

echo "=== [2/5] Format Check ==="
uv run ruff format --check .
echo "✓ Format check passed"
echo ""

echo "=== [3/5] Type Check ==="
uv run mypy src/ --strict --ignore-missing-imports
echo "✓ Type check passed"
echo ""

echo "=== [4/5] Security Scan ==="
uv run bandit -r src/ -q -s B101
echo "✓ Security scan passed"
echo ""

echo "=== [5/5] Unit Tests ==="
uv run pytest tests/unit/ -v --tb=short
echo "✓ Unit tests passed"
echo ""

echo "============================================"
echo "  All CI checks passed ✓"
echo "============================================"
