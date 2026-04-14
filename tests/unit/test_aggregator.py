from decimal import Decimal

from wt_video_cal.aggregator import aggregate, apply_manager_gmv_adjustments
from wt_video_cal.config import AccountInfo, AppConfig
from wt_video_cal.models import CommissionResult, Currency, VideoRecord


def _make_result(
    creator: str,
    video_id: str,
    manager: str,
    region: str,
    gmv_cny: str,
    profit_cny: str,
    commission: str,
    orders: int = 1,
    items_sold: int = 1,
) -> CommissionResult:
    record = VideoRecord(
        creator_name=creator,
        video_id=video_id,
        product_name="Product",
        attributed_gmv=Decimal("100"),
        orders=orders,
        items_sold=items_sold,
        currency=Currency.USD,
        source_file="test.xlsx",
    )
    return CommissionResult(
        record=record,
        account=creator,
        region=region,
        manager=manager,
        exchange_rate=Decimal("7.25"),
        gmv_cny=Decimal(gmv_cny),
        profit_margin=Decimal("0.30"),
        profit_cny=Decimal(profit_cny),
        commission=Decimal(commission),
    )


class TestAggregate:
    def test_single_manager_single_account(self) -> None:
        results = [
            _make_result("acct1", "v1", "张三", "美国", "725", "217.50", "10.88", 5, 6),
            _make_result("acct1", "v2", "张三", "美国", "1450", "435", "21.75", 10, 12),
        ]
        managers = aggregate(results)
        assert len(managers) == 1
        ms = managers["张三"]
        assert ms.total_orders == 15
        assert ms.total_items_sold == 18
        assert ms.total_gmv_cny == Decimal("2175")
        assert ms.total_commission == Decimal("32.63")
        assert len(ms.accounts) == 1
        assert ms.accounts["acct1"].total_orders == 15

    def test_single_manager_multiple_accounts(self) -> None:
        results = [
            _make_result("acct1", "v1", "张三", "美国", "725", "217.50", "10.88", 5, 6),
            _make_result("acct2", "v2", "张三", "英国", "920", "276", "13.80", 3, 4),
        ]
        managers = aggregate(results)
        assert len(managers) == 1
        ms = managers["张三"]
        assert len(ms.accounts) == 2
        assert ms.total_orders == 8
        assert ms.total_gmv_cny == Decimal("1645")

    def test_multiple_managers(self) -> None:
        results = [
            _make_result("acct1", "v1", "张三", "美国", "725", "217.50", "10.88"),
            _make_result("acct2", "v2", "李四", "英国", "920", "276", "13.80"),
        ]
        managers = aggregate(results)
        assert len(managers) == 2
        assert "张三" in managers
        assert "李四" in managers

    def test_empty_results(self) -> None:
        managers = aggregate([])
        assert managers == {}

    def test_details_attached(self) -> None:
        results = [
            _make_result("acct1", "v1", "张三", "美国", "725", "217.50", "10.88"),
        ]
        managers = aggregate(results)
        acct = managers["张三"].accounts["acct1"]
        assert len(acct.details) == 1
        assert acct.details[0].record.video_id == "v1"

    def test_apply_manager_gmv_adjustments(self) -> None:
        results = [
            _make_result("acct1", "v1", "张三", "美国", "725", "217.50", "10.88", 5, 6),
            _make_result("acct2", "v2", "李四", "英国", "920", "276", "13.80", 3, 4),
        ]
        managers = aggregate(results)
        config = AppConfig(
            default_profit_margin=Decimal("0.30"),
            profit_rules=[],
            accounts={
                "acct1": AccountInfo(region="美国", manager="张三"),
                "acct2": AccountInfo(region="英国", manager="李四"),
            },
            manager_monthly_gmv_usd={"2026-01": {"张三": Decimal("150.00")}},
        )

        apply_manager_gmv_adjustments(
            managers,
            config,
            "2026-01",
            exchange_rate_usd=Decimal("7.25"),
            commission_rate=Decimal("0.05"),
        )

        assert managers["张三"].creator_side_gmv_usd == Decimal("150.00")
        assert managers["张三"].gmv_diff_usd == Decimal("50.00")
        assert managers["张三"].adjustment_commission_cny == Decimal("5.44")
        assert managers["张三"].total_commission_with_adjustment == Decimal("16.32")
        assert managers["李四"].creator_side_gmv_usd is None
        assert managers["李四"].gmv_diff_usd is None
        assert managers["李四"].adjustment_commission_cny == Decimal("0")
