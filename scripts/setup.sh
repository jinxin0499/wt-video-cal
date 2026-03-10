#!/usr/bin/env bash
# 初始化开发环境
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== 安装依赖 ==="
uv sync

echo ""
echo "=== 创建数据目录 ==="
mkdir -p data output

echo ""
echo "=== 验证环境 ==="
uv run python -c "import wt_video_cal; print('wt_video_cal 导入成功')"
uv run python -c "import openpyxl; print(f'openpyxl {openpyxl.__version__}')"

echo ""
echo "✅ 环境就绪"
echo ""
echo "下一步："
echo "  1. 修改 src/wt_video_cal/settings.py 中的月份和汇率"
echo "  2. 将导出的 Excel 文件放入 data/ 目录"
echo "  3. 运行 scripts/run.sh"
