from decimal import Decimal

from wt_video_cal.models import (
    AccountSummary,
    CommissionResult,
    Currency,
    ExcelFormat,
    ManagerSummary,
    VideoRecord,
)


class TestCurrency:
    def test_usd(self) -> None:
        assert Currency.USD.value == "USD"

    def test_gbp(self) -> None:
        assert Currency.GBP.value == "GBP"


class TestExcelFormat:
    def test_formats(self) -> None:
        assert ExcelFormat.CHINESE_USD.value == "chinese_usd"
        assert ExcelFormat.ENGLISH_USD.value == "english_usd"
        assert ExcelFormat.ENGLISH_GBP.value == "english_gbp"


class TestVideoRecord:
    def test_create(self) -> None:
        record = VideoRecord(
            creator_name="test_user",
            video_id="123456",
            product_name="Test Product",
            attributed_gmv=Decimal("100.50"),
            orders=5,
            items_sold=6,
            currency=Currency.USD,
            source_file="test.xlsx",
        )
        assert record.creator_name == "test_user"
        assert record.attributed_gmv == Decimal("100.50")
        assert record.currency == Currency.USD

    def test_frozen(self) -> None:
        record = VideoRecord(
            creator_name="test",
            video_id="1",
            product_name="p",
            attributed_gmv=Decimal("0"),
            orders=0,
            items_sold=0,
            currency=Currency.USD,
            source_file="f",
        )
        try:
            record.creator_name = "other"  # type: ignore[misc]
            assert False, "Should raise"
        except AttributeError:
            pass


class TestCommissionResult:
    def test_create(self) -> None:
        record = VideoRecord(
            creator_name="user1",
            video_id="v1",
            product_name="Product",
            attributed_gmv=Decimal("1000"),
            orders=10,
            items_sold=12,
            currency=Currency.USD,
            source_file="test.xlsx",
        )
        result = CommissionResult(
            record=record,
            account="shop1",
            region="美国",
            manager="张三",
            exchange_rate=Decimal("7.25"),
            gmv_cny=Decimal("7250"),
            profit_margin=Decimal("0.30"),
            profit_cny=Decimal("2175"),
            commission=Decimal("108.75"),
        )
        assert result.commission == Decimal("108.75")


class TestAccountSummary:
    def test_defaults(self) -> None:
        summary = AccountSummary(account="shop1", region="美国", manager="张三")
        assert summary.total_orders == 0
        assert summary.total_commission == Decimal("0")
        assert summary.details == []


class TestManagerSummary:
    def test_defaults(self) -> None:
        summary = ManagerSummary(manager="张三")
        assert summary.total_orders == 0
        assert summary.accounts == {}
