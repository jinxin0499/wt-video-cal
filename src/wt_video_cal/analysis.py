"""数据分析模块：从提成明细中计算各种排名和分布。"""

from dataclasses import dataclass, field
from decimal import Decimal

from wt_video_cal.models import CommissionResult, ManagerSummary


@dataclass(frozen=True)
class RankedVideo:
    """视频排名条目。"""

    rank: int
    video_id: str
    product_name: str
    account: str
    orders: int
    items_sold: int
    gmv_cny: Decimal


@dataclass(frozen=True)
class RankedProduct:
    """商品排名条目。"""

    rank: int
    product_name: str
    orders: int
    items_sold: int
    gmv_cny: Decimal
    items_pct: Decimal  # 件数占比
    gmv_pct: Decimal  # GMV占比


@dataclass(frozen=True)
class AccountRanking:
    """账号排名条目。"""

    rank: int
    account: str
    manager: str
    region: str
    orders: int
    items_sold: int
    gmv_cny: Decimal
    commission: Decimal
    unit_price: Decimal  # 客单价 = GMV / 订单数


@dataclass(frozen=True)
class RegionBreakdown:
    """区域分布条目。"""

    region: str
    account_count: int
    orders: int
    items_sold: int
    gmv_cny: Decimal
    commission: Decimal
    gmv_pct: Decimal


@dataclass(frozen=True)
class MarginBucket:
    """利润率分布条目。"""

    margin: str
    product_count: int
    orders: int
    items_sold: int
    gmv_cny: Decimal
    gmv_pct: Decimal


@dataclass
class AnalysisResult:
    """汇总所有分析表。"""

    top_videos_by_orders: list[RankedVideo] = field(default_factory=list)
    top_videos_by_gmv: list[RankedVideo] = field(default_factory=list)
    top_products_by_items: list[RankedProduct] = field(default_factory=list)
    top_products_by_gmv: list[RankedProduct] = field(default_factory=list)
    account_rankings: list[AccountRanking] = field(default_factory=list)
    region_breakdown: list[RegionBreakdown] = field(default_factory=list)
    margin_distribution: list[MarginBucket] = field(default_factory=list)


def compute_analysis(
    details: list[CommissionResult], *, top_n: int = 10
) -> AnalysisResult:
    """从提成明细中计算所有分析指标。"""
    if not details:
        return AnalysisResult()

    total_items = sum(d.record.items_sold for d in details)
    total_gmv = sum((d.gmv_cny for d in details), Decimal("0"))

    result = AnalysisResult()
    result.top_videos_by_orders = _rank_videos(details, key="orders", top_n=top_n)
    result.top_videos_by_gmv = _rank_videos(details, key="gmv", top_n=top_n)
    result.top_products_by_items = _rank_products(
        details, key="items", top_n=top_n,
        total_items=total_items, total_gmv=total_gmv,
    )
    result.top_products_by_gmv = _rank_products(
        details, key="gmv", top_n=top_n,
        total_items=total_items, total_gmv=total_gmv,
    )
    result.account_rankings = _rank_accounts(details)
    result.region_breakdown = _compute_region_breakdown(details, total_gmv)
    result.margin_distribution = _compute_margin_distribution(details, total_gmv)
    return result


def _rank_videos(
    details: list[CommissionResult], *, key: str, top_n: int
) -> list[RankedVideo]:
    """按视频聚合并排名。"""
    agg: dict[str, dict[str, object]] = {}
    for d in details:
        vid = d.record.video_id
        if vid not in agg:
            agg[vid] = {
                "video_id": vid,
                "product_name": d.record.product_name,
                "account": d.account,
                "orders": 0,
                "items_sold": 0,
                "gmv_cny": Decimal("0"),
            }
        agg[vid]["orders"] += d.record.orders  # type: ignore[operator]
        agg[vid]["items_sold"] += d.record.items_sold  # type: ignore[operator]
        agg[vid]["gmv_cny"] += d.gmv_cny  # type: ignore[operator]

    sort_key = "orders" if key == "orders" else "gmv_cny"
    ranked = sorted(agg.values(), key=lambda x: x[sort_key], reverse=True)[:top_n]  # type: ignore[arg-to-sorted]

    return [
        RankedVideo(
            rank=i + 1,
            video_id=v["video_id"],  # type: ignore[arg-type]
            product_name=v["product_name"],  # type: ignore[arg-type]
            account=v["account"],  # type: ignore[arg-type]
            orders=v["orders"],  # type: ignore[arg-type]
            items_sold=v["items_sold"],  # type: ignore[arg-type]
            gmv_cny=v["gmv_cny"],  # type: ignore[arg-type]
        )
        for i, v in enumerate(ranked)
    ]


def _rank_products(
    details: list[CommissionResult],
    *,
    key: str,
    top_n: int,
    total_items: int,
    total_gmv: Decimal,
) -> list[RankedProduct]:
    """按商品聚合并排名。"""
    agg: dict[str, dict[str, object]] = {}
    for d in details:
        pn = d.record.product_name
        if pn not in agg:
            agg[pn] = {
                "product_name": pn,
                "orders": 0,
                "items_sold": 0,
                "gmv_cny": Decimal("0"),
            }
        agg[pn]["orders"] += d.record.orders  # type: ignore[operator]
        agg[pn]["items_sold"] += d.record.items_sold  # type: ignore[operator]
        agg[pn]["gmv_cny"] += d.gmv_cny  # type: ignore[operator]

    sort_key = "items_sold" if key == "items" else "gmv_cny"
    ranked = sorted(agg.values(), key=lambda x: x[sort_key], reverse=True)[:top_n]  # type: ignore[arg-to-sorted]

    return [
        RankedProduct(
            rank=i + 1,
            product_name=p["product_name"],  # type: ignore[arg-type]
            orders=p["orders"],  # type: ignore[arg-type]
            items_sold=p["items_sold"],  # type: ignore[arg-type]
            gmv_cny=p["gmv_cny"],  # type: ignore[arg-type]
            items_pct=Decimal(str(p["items_sold"])) / Decimal(str(total_items)) * 100
            if total_items > 0
            else Decimal("0"),
            gmv_pct=p["gmv_cny"] / total_gmv * 100  # type: ignore[operator]
            if total_gmv > 0
            else Decimal("0"),
        )
        for i, p in enumerate(ranked)
    ]


def _rank_accounts(details: list[CommissionResult]) -> list[AccountRanking]:
    """按账号聚合并排名（按GMV降序）。"""
    agg: dict[str, dict[str, object]] = {}
    for d in details:
        acct = d.account
        if acct not in agg:
            agg[acct] = {
                "account": acct,
                "manager": d.manager,
                "region": d.region,
                "orders": 0,
                "items_sold": 0,
                "gmv_cny": Decimal("0"),
                "commission": Decimal("0"),
            }
        agg[acct]["orders"] += d.record.orders  # type: ignore[operator]
        agg[acct]["items_sold"] += d.record.items_sold  # type: ignore[operator]
        agg[acct]["gmv_cny"] += d.gmv_cny  # type: ignore[operator]
        agg[acct]["commission"] += d.commission  # type: ignore[operator]

    ranked = sorted(agg.values(), key=lambda x: x["gmv_cny"], reverse=True)  # type: ignore[arg-to-sorted]

    return [
        AccountRanking(
            rank=i + 1,
            account=a["account"],  # type: ignore[arg-type]
            manager=a["manager"],  # type: ignore[arg-type]
            region=a["region"],  # type: ignore[arg-type]
            orders=a["orders"],  # type: ignore[arg-type]
            items_sold=a["items_sold"],  # type: ignore[arg-type]
            gmv_cny=a["gmv_cny"],  # type: ignore[arg-type]
            commission=a["commission"],  # type: ignore[arg-type]
            unit_price=a["gmv_cny"] / a["orders"]  # type: ignore[operator]
            if a["orders"] > 0  # type: ignore[operator]
            else Decimal("0"),
        )
        for i, a in enumerate(ranked)
    ]


def _compute_region_breakdown(
    details: list[CommissionResult], total_gmv: Decimal
) -> list[RegionBreakdown]:
    """按区域聚合。"""
    agg: dict[str, dict[str, object]] = {}
    for d in details:
        region = d.region
        if region not in agg:
            agg[region] = {
                "region": region,
                "accounts": set(),
                "orders": 0,
                "items_sold": 0,
                "gmv_cny": Decimal("0"),
                "commission": Decimal("0"),
            }
        agg[region]["accounts"].add(d.account)  # type: ignore[union-attr]
        agg[region]["orders"] += d.record.orders  # type: ignore[operator]
        agg[region]["items_sold"] += d.record.items_sold  # type: ignore[operator]
        agg[region]["gmv_cny"] += d.gmv_cny  # type: ignore[operator]
        agg[region]["commission"] += d.commission  # type: ignore[operator]

    ranked = sorted(agg.values(), key=lambda x: x["gmv_cny"], reverse=True)  # type: ignore[arg-to-sorted]

    return [
        RegionBreakdown(
            region=r["region"],  # type: ignore[arg-type]
            account_count=len(r["accounts"]),  # type: ignore[arg-type]
            orders=r["orders"],  # type: ignore[arg-type]
            items_sold=r["items_sold"],  # type: ignore[arg-type]
            gmv_cny=r["gmv_cny"],  # type: ignore[arg-type]
            commission=r["commission"],  # type: ignore[arg-type]
            gmv_pct=r["gmv_cny"] / total_gmv * 100  # type: ignore[operator]
            if total_gmv > 0
            else Decimal("0"),
        )
        for r in ranked
    ]


def _compute_margin_distribution(
    details: list[CommissionResult], total_gmv: Decimal
) -> list[MarginBucket]:
    """按利润率分布聚合。"""
    agg: dict[str, dict[str, object]] = {}
    for d in details:
        margin_str = f"{float(d.profit_margin * 100):.0f}%"
        if margin_str not in agg:
            agg[margin_str] = {
                "margin": margin_str,
                "margin_val": d.profit_margin,
                "products": set(),
                "orders": 0,
                "items_sold": 0,
                "gmv_cny": Decimal("0"),
            }
        agg[margin_str]["products"].add(d.record.product_name)  # type: ignore[union-attr]
        agg[margin_str]["orders"] += d.record.orders  # type: ignore[operator]
        agg[margin_str]["items_sold"] += d.record.items_sold  # type: ignore[operator]
        agg[margin_str]["gmv_cny"] += d.gmv_cny  # type: ignore[operator]

    ranked = sorted(agg.values(), key=lambda x: x["gmv_cny"], reverse=True)  # type: ignore[arg-to-sorted]

    return [
        MarginBucket(
            margin=m["margin"],  # type: ignore[arg-type]
            product_count=len(m["products"]),  # type: ignore[arg-type]
            orders=m["orders"],  # type: ignore[arg-type]
            items_sold=m["items_sold"],  # type: ignore[arg-type]
            gmv_cny=m["gmv_cny"],  # type: ignore[arg-type]
            gmv_pct=m["gmv_cny"] / total_gmv * 100  # type: ignore[operator]
            if total_gmv > 0
            else Decimal("0"),
        )
        for m in ranked
    ]


def extract_all_details(
    managers: dict[str, ManagerSummary],
) -> list[CommissionResult]:
    """从所有负责人汇总中提取全部明细。"""
    details: list[CommissionResult] = []
    for ms in managers.values():
        details.extend(extract_manager_details(ms))
    return details


def extract_manager_details(manager_summary: ManagerSummary) -> list[CommissionResult]:
    """从单个负责人汇总中提取全部明细。"""
    details: list[CommissionResult] = []
    for acct in manager_summary.accounts.values():
        details.extend(acct.details)
    return details
