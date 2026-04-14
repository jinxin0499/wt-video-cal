from decimal import Decimal

# ===== 每次运行前修改以下配置 =====
REPORT_MONTH = "2026-03"
EXCHANGE_RATE_USD = Decimal("6.8649")
EXCHANGE_RATE_GBP = Decimal("9.1633")
EXCHANGE_RATE_JPY = Decimal("0.043158")
COMMISSION_RATE = Decimal("0.05")

INPUT_DIR = "./data"
OUTPUT_DIR = "./output"
CONFIG_PATH = "./config/config.toml"
