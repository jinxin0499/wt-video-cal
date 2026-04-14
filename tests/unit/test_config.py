from decimal import Decimal
from pathlib import Path

import pytest

from wt_video_cal.config import AccountInfo, AppConfig, ProfitRule, load_config
from wt_video_cal.exceptions import ConfigError


@pytest.fixture
def sample_toml(tmp_path: Path) -> Path:
    content = """\
[profit_margins]
default = 0.30

[[profit_margins.rules]]
pattern = "5000"
margin = 0.15
max_unit_price_cny = 100
description = "5000mAh充电宝"

[accounts.artcyber6]
region = "美国"
manager = "古嘉垚"

[accounts.user9120702396325]
region = "美国"
manager = "刘龙海"

[manager_monthly_gmv_usd."2026-01"]
"古嘉垚" = 4567.89
"""
    p = tmp_path / "config.toml"
    p.write_text(content, encoding="utf-8")
    return p


class TestLoadConfig:
    def test_load_success(self, sample_toml: Path) -> None:
        config = load_config(sample_toml)
        assert config.default_profit_margin == Decimal("0.30")
        assert len(config.profit_rules) == 1
        assert config.profit_rules[0].pattern == "5000"
        assert config.profit_rules[0].margin == Decimal("0.15")
        assert config.profit_rules[0].max_unit_price_cny == Decimal("100")
        assert len(config.accounts) == 2
        assert config.get_manager_monthly_gmv_usd("2026-01", "古嘉垚") == Decimal("4567.89")

    def test_load_missing_file(self) -> None:
        with pytest.raises(ConfigError, match="配置文件不存在"):
            load_config("/nonexistent/config.toml")


class TestAppConfig:
    @pytest.fixture
    def config(self) -> AppConfig:
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
                "artcyber6": AccountInfo(region="美国", manager="古嘉垚"),
                "User9120702396325": AccountInfo(region="美国", manager="刘龙海"),
            },
        )

    def test_get_account_info_exact(self, config: AppConfig) -> None:
        info = config.get_account_info("artcyber6")
        assert info is not None
        assert info.manager == "古嘉垚"

    def test_get_account_info_case_insensitive(self, config: AppConfig) -> None:
        info = config.get_account_info("ArtCyber6")
        assert info is not None
        assert info.manager == "古嘉垚"

    def test_get_account_info_not_found(self, config: AppConfig) -> None:
        assert config.get_account_info("nonexistent") is None

    def test_get_profit_margin_match(self, config: AppConfig) -> None:
        margin = config.get_profit_margin(
            "Magnetic Wireless Power Bank 5000mAh - Portable charger",
            unit_price_cny=Decimal("99.99"),
        )
        assert margin == Decimal("0.15")

    def test_get_profit_margin_case_insensitive(self, config: AppConfig) -> None:
        margin = config.get_profit_margin(
            "power bank 5000MAH charger",
            unit_price_cny=Decimal("80"),
        )
        assert margin == Decimal("0.15")

    def test_get_profit_margin_default_for_non_matching_product(self, config: AppConfig) -> None:
        margin = config.get_profit_margin("Smart Watch Gift Set", unit_price_cny=Decimal("50"))
        assert margin == Decimal("0.30")

    def test_get_profit_margin_default_when_unit_price_too_high(self, config: AppConfig) -> None:
        margin = config.get_profit_margin(
            "Magnetic Wireless Power Bank 5000mAh - Portable charger",
            unit_price_cny=Decimal("100"),
        )
        assert margin == Decimal("0.30")

    def test_get_low_margin_review_rules(self, config: AppConfig) -> None:
        reviews = config.get_low_margin_review_rules(
            "Magnetic Wireless Power Bank 5000mAh - Portable charger",
            unit_price_cny=Decimal("120"),
        )
        assert len(reviews) == 1
        rule, reason = reviews[0]
        assert rule.pattern == "5000"
        assert reason == "件单价CNY超过阈值"

    def test_get_low_margin_review_rules_for_missing_unit_price(self, config: AppConfig) -> None:
        reviews = config.get_low_margin_review_rules(
            "Magnetic Wireless Power Bank 5000mAh - Portable charger"
        )
        assert len(reviews) == 1
        _, reason = reviews[0]
        assert reason == "成交件数=0，无法判定件单价"

    def test_get_profit_margin_default(self, config: AppConfig) -> None:
        margin = config.get_profit_margin("power bank 5000MAH charger")
        assert margin == Decimal("0.30")

    def test_get_manager_monthly_gmv_usd(self, config: AppConfig) -> None:
        config.manager_monthly_gmv_usd["2026-03"] = {"古嘉垚": Decimal("888.88")}
        assert config.get_manager_monthly_gmv_usd("2026-03", "古嘉垚") == Decimal("888.88")
        assert config.get_manager_monthly_gmv_usd("2026-03", "刘龙海") is None


class TestLoadRealConfig:
    def test_load_project_config(self) -> None:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.toml"
        if config_path.exists():
            config = load_config(config_path)
            assert len(config.accounts) == 30
            assert config.default_profit_margin == Decimal("0.30")
