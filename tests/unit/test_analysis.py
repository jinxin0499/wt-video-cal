from decimal import Decimal

from wt_video_cal.analysis import (
    compute_analysis,
    extract_all_details,
    extract_manager_details,
)
from wt_video_cal.models import (
    AccountSummary,
    CommissionResult,
    Currency,
    ManagerSummary,
    VideoRecord,
)


def _make_detail(
    video_id: str = "v1",
    product: str = "Product A",
    account: str = "acct1",
    region: str = "美国",
    manager: str = "张三",
    orders: int = 5,
    items_sold: int = 6,
    gmv: Decimal = Decimal("100"),
    gmv_cny: Decimal = Decimal("725"),
    profit_margin: Decimal = Decimal("0.30"),
    commission: Decimal = Decimal("10.88"),
) -> CommissionResult:
    record = VideoRecord(
        account, video_id, product, gmv, orders, items_sold,
        Currency.USD, "test.xlsx",
    )
    return CommissionResult(
        record=record,
        account=account,
        region=region,
        manager=manager,
        exchange_rate=Decimal("7.25"),
        gmv_cny=gmv_cny,
        profit_margin=profit_margin,
        profit_cny=gmv_cny * profit_margin,
        commission=commission,
    )


class TestComputeAnalysisEmpty:
    def test_empty_returns_empty_result(self) -> None:
        result = compute_analysis([])
        assert result.top_videos_by_orders == []
        assert result.top_videos_by_gmv == []
        assert result.top_products_by_items == []
        assert result.top_products_by_gmv == []
        assert result.account_rankings == []
        assert result.region_breakdown == []
        assert result.margin_distribution == []


class TestComputeAnalysisSmallData:
    def test_video_ranking_by_orders(self) -> None:
        details = [
            _make_detail(video_id="v1", orders=10, gmv_cny=Decimal("100")),
            _make_detail(video_id="v2", orders=20, gmv_cny=Decimal("50")),
        ]
        result = compute_analysis(details)
        assert len(result.top_videos_by_orders) == 2
        assert result.top_videos_by_orders[0].video_id == "v2"
        assert result.top_videos_by_orders[0].rank == 1
        assert result.top_videos_by_orders[0].orders == 20
        assert result.top_videos_by_orders[1].video_id == "v1"
        assert result.top_videos_by_orders[1].rank == 2

    def test_video_ranking_by_gmv(self) -> None:
        details = [
            _make_detail(video_id="v1", orders=10, gmv_cny=Decimal("100")),
            _make_detail(video_id="v2", orders=20, gmv_cny=Decimal("50")),
        ]
        result = compute_analysis(details)
        assert result.top_videos_by_gmv[0].video_id == "v1"
        assert result.top_videos_by_gmv[0].gmv_cny == Decimal("100")

    def test_product_ranking_with_percentages(self) -> None:
        details = [
            _make_detail(product="PA", items_sold=10, gmv_cny=Decimal("200")),
            _make_detail(product="PB", items_sold=30, gmv_cny=Decimal("800")),
        ]
        result = compute_analysis(details)
        # By items: PB first (30 items)
        assert result.top_products_by_items[0].product_name == "PB"
        assert result.top_products_by_items[0].items_sold == 30
        # items_pct = 30/40 * 100 = 75%
        assert result.top_products_by_items[0].items_pct == Decimal("75")
        # gmv_pct = 800/1000 * 100 = 80%
        assert result.top_products_by_items[0].gmv_pct == Decimal("80")

    def test_account_ranking_with_unit_price(self) -> None:
        details = [
            _make_detail(
                account="a1", orders=10,
                gmv_cny=Decimal("1000"), commission=Decimal("50"),
            ),
            _make_detail(
                account="a2", orders=5,
                gmv_cny=Decimal("500"), commission=Decimal("25"),
            ),
        ]
        result = compute_analysis(details)
        assert len(result.account_rankings) == 2
        # a1 first (higher GMV)
        assert result.account_rankings[0].account == "a1"
        assert result.account_rankings[0].unit_price == Decimal("100")  # 1000/10
        assert result.account_rankings[1].unit_price == Decimal("100")  # 500/5

    def test_region_breakdown(self) -> None:
        details = [
            _make_detail(
                account="a1", region="美国",
                gmv_cny=Decimal("600"), commission=Decimal("30"),
            ),
            _make_detail(
                account="a2", region="英国",
                gmv_cny=Decimal("400"), commission=Decimal("20"),
            ),
        ]
        result = compute_analysis(details)
        assert len(result.region_breakdown) == 2
        # 美国 first (higher GMV)
        assert result.region_breakdown[0].region == "美国"
        assert result.region_breakdown[0].account_count == 1
        # gmv_pct = 600/1000 * 100 = 60%
        assert result.region_breakdown[0].gmv_pct == Decimal("60")
        assert result.region_breakdown[1].gmv_pct == Decimal("40")

    def test_margin_distribution(self) -> None:
        details = [
            _make_detail(profit_margin=Decimal("0.30"), gmv_cny=Decimal("700")),
            _make_detail(profit_margin=Decimal("0.20"), gmv_cny=Decimal("300")),
        ]
        result = compute_analysis(details)
        assert len(result.margin_distribution) == 2
        # 30% margin first (higher GMV)
        assert result.margin_distribution[0].margin == "30%"
        assert result.margin_distribution[0].gmv_pct == Decimal("70")


class TestTopNParameter:
    def test_top_n_limits_results(self) -> None:
        details = [
            _make_detail(video_id=f"v{i}", product=f"P{i}", orders=i, gmv_cny=Decimal(str(i * 100)))
            for i in range(1, 21)
        ]
        result = compute_analysis(details, top_n=5)
        assert len(result.top_videos_by_orders) == 5
        assert len(result.top_videos_by_gmv) == 5
        assert len(result.top_products_by_items) == 5
        assert len(result.top_products_by_gmv) == 5


class TestDivisionByZeroProtection:
    def test_zero_orders_unit_price(self) -> None:
        details = [
            _make_detail(account="a1", orders=0, gmv_cny=Decimal("100")),
        ]
        result = compute_analysis(details)
        assert result.account_rankings[0].unit_price == Decimal("0")


class TestExtractDetails:
    def _make_manager(self) -> ManagerSummary:
        cr1 = _make_detail(account="a1", video_id="v1")
        cr2 = _make_detail(account="a2", video_id="v2")
        acct1 = AccountSummary(
            account="a1", region="美国", manager="张三", details=[cr1],
        )
        acct2 = AccountSummary(
            account="a2", region="英国", manager="张三", details=[cr2],
        )
        return ManagerSummary(
            manager="张三", accounts={"a1": acct1, "a2": acct2},
        )

    def test_extract_manager_details(self) -> None:
        ms = self._make_manager()
        details = extract_manager_details(ms)
        assert len(details) == 2

    def test_extract_all_details(self) -> None:
        ms = self._make_manager()
        managers = {"张三": ms}
        details = extract_all_details(managers)
        assert len(details) == 2
