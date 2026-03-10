from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class Currency(Enum):
    USD = "USD"
    GBP = "GBP"


class ExcelFormat(Enum):
    CHINESE_USD = "chinese_usd"
    ENGLISH_USD = "english_usd"
    ENGLISH_GBP = "english_gbp"


@dataclass(frozen=True)
class VideoRecord:
    """一行规范化的视频数据。"""

    creator_name: str
    video_id: str
    product_name: str
    attributed_gmv: Decimal
    orders: int
    items_sold: int
    currency: Currency
    source_file: str


@dataclass(frozen=True)
class CommissionResult:
    """单条提成计算结果。"""

    record: VideoRecord
    account: str
    region: str
    manager: str
    exchange_rate: Decimal
    gmv_cny: Decimal
    profit_margin: Decimal
    profit_cny: Decimal
    commission: Decimal


@dataclass
class AccountSummary:
    """单账号汇总。"""

    account: str
    region: str
    manager: str
    total_orders: int = 0
    total_items_sold: int = 0
    total_gmv_cny: Decimal = Decimal("0")
    total_profit_cny: Decimal = Decimal("0")
    total_commission: Decimal = Decimal("0")
    details: list[CommissionResult] = field(default_factory=list)


@dataclass
class ManagerSummary:
    """单负责人汇总。"""

    manager: str
    total_orders: int = 0
    total_items_sold: int = 0
    total_gmv_cny: Decimal = Decimal("0")
    total_profit_cny: Decimal = Decimal("0")
    total_commission: Decimal = Decimal("0")
    accounts: dict[str, AccountSummary] = field(default_factory=dict)
