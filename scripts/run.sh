#!/usr/bin/env bash
# 运行提成计算（主入口）
# 使用前请先修改 src/wt_video_cal/settings.py 中的月份和汇率
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== 运行提成计算 ==="
echo "请确认已修改 settings.py 中的配置（月份、汇率）"
echo ""

uv run python -m wt_video_cal
