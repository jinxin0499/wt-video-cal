from decimal import Decimal

from wt_video_cal.__main__ import _build_low_margin_review_items
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
            )
        ],
        accounts={
            "acct1": AccountInfo(region="美国", manager="张三"),
        },
    )


class TestBuildLowMarginReviewItems:
    def test_excludes_zero_sales_records(self) -> None:
        config = _make_config()
        records = [
            VideoRecord(
                creator_name="acct1",
                video_id="v-zero",
                product_name="5000mAh charger",
                attributed_gmv=Decimal("0"),
                orders=0,
                items_sold=0,
                currency=Currency.USD,
                source_file="f.xlsx",
                video_gmv=Decimal("120"),
            ),
            VideoRecord(
                creator_name="acct1",
                video_id="v-high",
                product_name="5000mAh charger",
                attributed_gmv=Decimal("120"),
                orders=1,
                items_sold=1,
                currency=Currency.USD,
                source_file="f.xlsx",
                video_gmv=Decimal("120"),
            ),
        ]

        items = _build_low_margin_review_items(
            records,
            config,
            exchange_rate_usd=Decimal("7.25"),
            exchange_rate_gbp=Decimal("9.20"),
            exchange_rate_jpy=Decimal("0.04315"),
        )

        assert len(items) == 1
        assert items[0].video_id == "v-high"
        assert items[0].reason == "件单价CNY超过阈值"
