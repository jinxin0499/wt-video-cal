from decimal import Decimal

from wt_video_cal.calculator import UNKNOWN_MANAGER, calculate_all, calculate_commission
from wt_video_cal.config import AccountInfo, AppConfig, ProfitRule
from wt_video_cal.models import Currency, VideoRecord


def _make_config() -> AppConfig:
    return AppConfig(
        default_profit_margin=Decimal("0.30"),
        profit_rules=[
            ProfitRule(
                pattern="5000",
                margin=Decimal("0.15"),
                description="5000mAh",
                max_unit_price_cny=Decimal("100"),
            ),
        ],
        accounts={
            "digital_goodies_us": AccountInfo(region="美国", manager="古嘉垚"),
            "user9120702396325": AccountInfo(region="美国", manager="刘龙海"),
            "trendyitemspot": AccountInfo(region="英国", manager="刘龙海"),
            "user6594846791525": AccountInfo(region="日本", manager="古嘉垚"),
        },
    )


class TestCalculateCommission:
    def test_usd_default_margin(self) -> None:
        """USD + 默认利润率 30%: 3030.93 × 7.25 × 0.30 × 0.05"""
        config = _make_config()
        record = VideoRecord(
            creator_name="digital_goodies_us",
            video_id="v1",
            product_name="4-in-1 Magnetic Power Bank Set",
            attributed_gmv=Decimal("3030.93"),
            orders=155,
            items_sold=164,
            currency=Currency.USD,
            source_file="test.xlsx",
            video_gmv=Decimal("2926.18"),
        )
        result = calculate_commission(
            record,
            config,
            exchange_rate_usd=Decimal("7.25"),
            exchange_rate_gbp=Decimal("9.20"),
            commission_rate=Decimal("0.05"),
        )
        assert result.manager == "古嘉垚"
        assert result.region == "美国"
        assert result.exchange_rate == Decimal("7.25")
        assert result.profit_margin == Decimal("0.30")
        # 3030.93 * 7.25 = 21974.24
        assert result.gmv_cny == Decimal("21974.24")
        # 21974.24 * 0.30 = 6592.27
        assert result.profit_cny == Decimal("6592.27")
        # 6592.27 * 0.05 = 329.61
        assert result.commission == Decimal("329.61")

    def test_usd_5000_margin(self) -> None:
        """USD + 5000mAh利润率 15%: 22.72 × 7.25 × 0.15 × 0.05"""
        config = _make_config()
        record = VideoRecord(
            creator_name="user9120702396325",
            video_id="v2",
            product_name="Magnetic Wireless Power Bank 5000mAh",
            attributed_gmv=Decimal("22.72"),
            orders=2,
            items_sold=2,
            currency=Currency.USD,
            source_file="test.xlsx",
            video_gmv=Decimal("22.72"),
        )
        result = calculate_commission(
            record,
            config,
            exchange_rate_usd=Decimal("7.25"),
            exchange_rate_gbp=Decimal("9.20"),
            commission_rate=Decimal("0.05"),
        )
        assert result.manager == "刘龙海"
        assert result.profit_margin == Decimal("0.15")
        # 22.72 * 7.25 = 164.72
        assert result.gmv_cny == Decimal("164.72")
        # 164.72 * 0.15 = 24.71
        assert result.profit_cny == Decimal("24.71")
        # 24.71 * 0.05 = 1.24
        assert result.commission == Decimal("1.24")

    def test_usd_5000_high_unit_price_uses_default_margin(self) -> None:
        config = _make_config()
        record = VideoRecord(
            creator_name="user9120702396325",
            video_id="v2h",
            product_name="Upgraded 6-in-1 Charging Kit 5000mAh",
            attributed_gmv=Decimal("120.00"),
            orders=4,
            items_sold=1,
            currency=Currency.USD,
            source_file="test.xlsx",
            video_gmv=Decimal("120.00"),
        )
        result = calculate_commission(
            record,
            config,
            exchange_rate_usd=Decimal("7.25"),
            exchange_rate_gbp=Decimal("9.20"),
            commission_rate=Decimal("0.05"),
        )
        assert result.profit_margin == Decimal("0.30")

    def test_gbp_conversion(self) -> None:
        """GBP + 默认利润率: 1552.14 × 9.20 × 0.30 × 0.05"""
        config = _make_config()
        record = VideoRecord(
            creator_name="trendyitemspot",
            video_id="v3",
            product_name="Upgraded 6-in-1 Magnetic Charging Kit",
            attributed_gmv=Decimal("1552.14"),
            orders=57,
            items_sold=60,
            currency=Currency.GBP,
            source_file="test.xlsx",
            video_gmv=Decimal("1248.35"),
        )
        result = calculate_commission(
            record,
            config,
            exchange_rate_usd=Decimal("7.25"),
            exchange_rate_gbp=Decimal("9.20"),
            commission_rate=Decimal("0.05"),
        )
        assert result.exchange_rate == Decimal("9.20")
        assert result.profit_margin == Decimal("0.30")
        # 1552.14 * 9.20 = 14279.69
        assert result.gmv_cny == Decimal("14279.69")
        # 14279.69 * 0.30 = 4283.91
        assert result.profit_cny == Decimal("4283.91")
        # 4283.91 * 0.05 = 214.20
        assert result.commission == Decimal("214.20")

    def test_jpy_conversion(self) -> None:
        """JPY + 默认利润率: 10000 × 0.04315 × 0.30 × 0.05"""
        config = _make_config()
        record = VideoRecord(
            creator_name="user6594846791525",
            video_id="vjp1",
            product_name="Compact Camera",
            attributed_gmv=Decimal("10000"),
            orders=12,
            items_sold=12,
            currency=Currency.JPY,
            source_file="test.xlsx",
            video_gmv=Decimal("12000"),
        )
        result = calculate_commission(
            record,
            config,
            exchange_rate_usd=Decimal("7.25"),
            exchange_rate_gbp=Decimal("9.20"),
            exchange_rate_jpy=Decimal("0.04315"),
            commission_rate=Decimal("0.05"),
        )
        assert result.region == "日本"
        assert result.manager == "古嘉垚"
        assert result.exchange_rate == Decimal("0.04315")
        assert result.gmv_cny == Decimal("431.50")
        assert result.profit_cny == Decimal("129.45")
        assert result.commission == Decimal("6.47")

    def test_unknown_account(self) -> None:
        """未知账号应归入 '未知负责人'。"""
        config = _make_config()
        record = VideoRecord(
            creator_name="unknown_account",
            video_id="v4",
            product_name="Some Product",
            attributed_gmv=Decimal("100"),
            orders=1,
            items_sold=1,
            currency=Currency.USD,
            source_file="test.xlsx",
            video_gmv=Decimal("100"),
        )
        result = calculate_commission(
            record,
            config,
            exchange_rate_usd=Decimal("7.25"),
            exchange_rate_gbp=Decimal("9.20"),
            exchange_rate_jpy=Decimal("0.04315"),
            commission_rate=Decimal("0.05"),
        )
        assert result.manager == UNKNOWN_MANAGER

    def test_zero_gmv(self) -> None:
        config = _make_config()
        record = VideoRecord(
            creator_name="digital_goodies_us",
            video_id="v5",
            product_name="Product",
            attributed_gmv=Decimal("0"),
            orders=0,
            items_sold=0,
            currency=Currency.USD,
            source_file="test.xlsx",
            video_gmv=Decimal("0"),
        )
        result = calculate_commission(
            record,
            config,
            exchange_rate_usd=Decimal("7.25"),
            exchange_rate_gbp=Decimal("9.20"),
            exchange_rate_jpy=Decimal("0.04315"),
            commission_rate=Decimal("0.05"),
        )
        assert result.gmv_cny == Decimal("0.00")
        assert result.commission == Decimal("0.00")


class TestCalculateAll:
    def test_batch(self) -> None:
        config = _make_config()
        records = [
            VideoRecord(
                "digital_goodies_us",
                "v1",
                "Product A",
                Decimal("100"),
                1,
                1,
                Currency.USD,
                "f",
                Decimal("100"),
            ),
            VideoRecord(
                "user9120702396325",
                "v2",
                "5000mAh Bank",
                Decimal("200"),
                2,
                2,
                Currency.USD,
                "f",
                Decimal("20"),
            ),
        ]
        results = calculate_all(
            records,
            config,
            exchange_rate_usd=Decimal("7.25"),
            exchange_rate_gbp=Decimal("9.20"),
            exchange_rate_jpy=Decimal("0.04315"),
            commission_rate=Decimal("0.05"),
        )
        assert len(results) == 2
        assert results[0].manager == "古嘉垚"
        assert results[1].manager == "刘龙海"
        assert results[1].profit_margin == Decimal("0.15")
