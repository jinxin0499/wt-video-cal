from decimal import ROUND_HALF_UP, Decimal

from wt_video_cal.config import AppConfig
from wt_video_cal.models import AccountSummary, CommissionResult, ManagerSummary

ADJUSTMENT_PROFIT_MARGIN = Decimal("0.30")


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def aggregate(results: list[CommissionResult]) -> dict[str, ManagerSummary]:
    """按 负责人 → 账号 两级分组汇总。"""
    managers: dict[str, ManagerSummary] = {}

    for r in results:
        # 获取或创建 ManagerSummary
        if r.manager not in managers:
            managers[r.manager] = ManagerSummary(manager=r.manager)
        ms = managers[r.manager]

        # 获取或创建 AccountSummary
        if r.account not in ms.accounts:
            ms.accounts[r.account] = AccountSummary(
                account=r.account,
                region=r.region,
                manager=r.manager,
            )
        acct = ms.accounts[r.account]

        # 累加账号级别
        acct.total_orders += r.record.orders
        acct.total_items_sold += r.record.items_sold
        acct.total_gmv_cny += r.gmv_cny
        acct.total_profit_cny += r.profit_cny
        acct.total_commission += r.commission
        acct.details.append(r)

        # 累加负责人级别
        ms.total_orders += r.record.orders
        ms.total_items_sold += r.record.items_sold
        ms.total_gmv_cny += r.gmv_cny
        ms.total_profit_cny += r.profit_cny
        ms.total_commission += r.commission

    return managers


def apply_manager_gmv_adjustments(
    managers: dict[str, ManagerSummary],
    config: AppConfig,
    report_month: str,
    *,
    exchange_rate_usd: Decimal,
    commission_rate: Decimal,
    adjustment_profit_margin: Decimal = ADJUSTMENT_PROFIT_MARGIN,
) -> None:
    """按月份配置补充负责人 GMV 差额补算。"""
    for summary in managers.values():
        creator_side_gmv_usd = config.get_manager_monthly_gmv_usd(report_month, summary.manager)
        if creator_side_gmv_usd is None:
            summary.creator_side_gmv_usd = None
            summary.gmv_diff_usd = None
            summary.adjustment_commission_cny = Decimal("0")
            continue

        backend_gmv_usd = (
            _round2(summary.total_gmv_cny / exchange_rate_usd)
            if exchange_rate_usd != Decimal("0")
            else Decimal("0")
        )
        gmv_diff_usd = _round2(creator_side_gmv_usd - backend_gmv_usd)
        adjustment_commission_cny = _round2(
            gmv_diff_usd * exchange_rate_usd * adjustment_profit_margin * commission_rate
        )

        summary.creator_side_gmv_usd = _round2(creator_side_gmv_usd)
        summary.gmv_diff_usd = gmv_diff_usd
        summary.adjustment_commission_cny = adjustment_commission_cny
