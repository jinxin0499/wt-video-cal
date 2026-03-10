import logging
from decimal import ROUND_HALF_UP, Decimal

from wt_video_cal.config import AppConfig
from wt_video_cal.models import CommissionResult, Currency, VideoRecord
from wt_video_cal.settings import COMMISSION_RATE, EXCHANGE_RATE_GBP, EXCHANGE_RATE_USD

logger = logging.getLogger(__name__)

UNKNOWN_MANAGER = "未知负责人"
UNKNOWN_REGION = "未知"


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_commission(
    record: VideoRecord,
    config: AppConfig,
    *,
    exchange_rate_usd: Decimal = EXCHANGE_RATE_USD,
    exchange_rate_gbp: Decimal = EXCHANGE_RATE_GBP,
    commission_rate: Decimal = COMMISSION_RATE,
) -> CommissionResult:
    """计算单条视频记录的提成。"""
    # 确定汇率
    if record.currency == Currency.GBP:
        exchange_rate = exchange_rate_gbp
    else:
        exchange_rate = exchange_rate_usd

    # 确定账号信息
    account_info = config.get_account_info(record.creator_name)
    if account_info:
        account = record.creator_name
        region = account_info.region
        manager = account_info.manager
    else:
        logger.warning("账号 '%s' 未在配置中找到，归入 '%s'", record.creator_name, UNKNOWN_MANAGER)
        account = record.creator_name
        region = UNKNOWN_REGION
        manager = UNKNOWN_MANAGER

    # 确定利润率
    profit_margin = config.get_profit_margin(record.product_name)

    # 计算: gmv × 汇率 × 利润率 × 提成比例
    gmv_cny = _round2(record.attributed_gmv * exchange_rate)
    profit_cny = _round2(gmv_cny * profit_margin)
    commission = _round2(profit_cny * commission_rate)

    return CommissionResult(
        record=record,
        account=account,
        region=region,
        manager=manager,
        exchange_rate=exchange_rate,
        gmv_cny=gmv_cny,
        profit_margin=profit_margin,
        profit_cny=profit_cny,
        commission=commission,
    )


def calculate_all(
    records: list[VideoRecord],
    config: AppConfig,
    *,
    exchange_rate_usd: Decimal = EXCHANGE_RATE_USD,
    exchange_rate_gbp: Decimal = EXCHANGE_RATE_GBP,
    commission_rate: Decimal = COMMISSION_RATE,
) -> list[CommissionResult]:
    """批量计算所有视频记录的提成。"""
    return [
        calculate_commission(
            r,
            config,
            exchange_rate_usd=exchange_rate_usd,
            exchange_rate_gbp=exchange_rate_gbp,
            commission_rate=commission_rate,
        )
        for r in records
    ]
