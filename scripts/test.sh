#!/usr/bin/env bash
# 运行所有测试 + 代码检查
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Ruff 代码检查 ==="
uv run ruff check src tests

echo ""
echo "=== Pyright 类型检查 ==="
uv run pyright src

echo ""
echo "=== Pytest 测试 ==="
uv run pytest -v --tb=short

echo ""
echo "✅ 全部通过"
