#!/usr/bin/env bash
# 清理输出文件和缓存
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== 清理输出目录 ==="
rm -rf output/*
echo "已清理 output/"

echo ""
echo "=== 清理 Python 缓存 ==="
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
echo "已清理缓存"
