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
description = "5000mAh充电宝"

[accounts.artcyber6]
region = "美国"
manager = "古嘉垚"

[accounts.user9120702396325]
region = "美国"
manager = "刘龙海"
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
        assert len(config.accounts) == 2

    def test_load_missing_file(self) -> None:
        with pytest.raises(ConfigError, match="配置文件不存在"):
            load_config("/nonexistent/config.toml")


class TestAppConfig:
    @pytest.fixture
    def config(self) -> AppConfig:
        return AppConfig(
            default_profit_margin=Decimal("0.30"),
            profit_rules=[
                ProfitRule(pattern="5000", margin=Decimal("0.15"), description="5000mAh"),
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
            "Magnetic Wireless Power Bank 5000mAh - Portable charger"
        )
        assert margin == Decimal("0.15")

    def test_get_profit_margin_case_insensitive(self, config: AppConfig) -> None:
        margin = config.get_profit_margin("power bank 5000MAH charger")
        assert margin == Decimal("0.15")

    def test_get_profit_margin_default(self, config: AppConfig) -> None:
        margin = config.get_profit_margin("Smart Watch Gift Set")
        assert margin == Decimal("0.30")


class TestLoadRealConfig:
    def test_load_project_config(self) -> None:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.toml"
        if config_path.exists():
            config = load_config(config_path)
            assert len(config.accounts) == 22
            assert config.default_profit_margin == Decimal("0.30")
