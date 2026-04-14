from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import TypedDict


class Currency(Enum):
    USD = "USD"
    GBP = "GBP"
    JPY = "JPY"


class ExcelFormat(Enum):
    CHINESE_USD = "chinese_usd"
    CHINESE_JPY = "chinese_jpy"
    ENGLISH_USD = "english_usd"
    ENGLISH_GBP = "english_gbp"
    ENGLISH_JPY = "english_jpy"


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
    video_gmv: Decimal = Decimal("0")


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


@dataclass(frozen=True)
class LowMarginReviewItem:
    """命中低毛利关键词但未按低毛利计算的复核记录。"""

    source_file: str
    manager: str
    account: str
    region: str
    video_id: str
    product_name: str
    currency: str
    video_gmv: Decimal
    orders: int
    items_sold: int
    unit_price_original: Decimal | None
    unit_price_cny: Decimal | None
    matched_pattern: str
    rule_margin: Decimal
    max_unit_price_cny: Decimal | None
    reason: str


class SourceCreatorStats(TypedDict):
    orders: int
    items_sold: int
    gmv: Decimal
    currency: str


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
    creator_side_gmv_usd: Decimal | None = None
    gmv_diff_usd: Decimal | None = None
    adjustment_commission_cny: Decimal = Decimal("0")

    @property
    def total_commission_with_adjustment(self) -> Decimal:
        return self.total_commission + self.adjustment_commission_cny
