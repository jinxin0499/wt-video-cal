import tomllib
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from wt_video_cal.exceptions import ConfigError


@dataclass(frozen=True)
class ProfitRule:
    pattern: str
    margin: Decimal
    description: str
    max_unit_price_cny: Decimal | None = None

    def keyword_matches(self, product_name: str) -> bool:
        return self.pattern.lower() in product_name.lower()

    def matches(self, product_name: str, *, unit_price_cny: Decimal | None = None) -> bool:
        if not self.keyword_matches(product_name):
            return False
        if self.max_unit_price_cny is None:
            return True
        if unit_price_cny is None:
            return False
        return unit_price_cny < self.max_unit_price_cny

    def get_skip_reason(
        self, product_name: str, *, unit_price_cny: Decimal | None = None
    ) -> str | None:
        if not self.keyword_matches(product_name) or self.max_unit_price_cny is None:
            return None
        if unit_price_cny is None:
            return "成交件数=0，无法判定件单价"
        if unit_price_cny >= self.max_unit_price_cny:
            return "件单价CNY超过阈值"
        return None


@dataclass(frozen=True)
class AccountInfo:
    region: str
    manager: str


@dataclass(frozen=True)
class AppConfig:
    default_profit_margin: Decimal
    profit_rules: list[ProfitRule]
    accounts: dict[str, AccountInfo]
    manager_monthly_gmv_usd: dict[str, dict[str, Decimal]] = field(default_factory=dict)

    def get_account_info(self, account_name: str) -> AccountInfo | None:
        """大小写不敏感地查找账号信息。"""
        lower = account_name.lower()
        for key, info in self.accounts.items():
            if key.lower() == lower:
                return info
        return None

    def get_manager_monthly_gmv_usd(self, report_month: str, manager: str) -> Decimal | None:
        """获取指定月份下负责人自行统计的 GMV(USD)。"""
        month_config = self.manager_monthly_gmv_usd.get(report_month)
        if month_config is None:
            return None
        return month_config.get(manager)

    def get_matching_profit_rule(
        self,
        product_name: str,
        *,
        unit_price_cny: Decimal | None = None,
    ) -> ProfitRule | None:
        """按规则顺序匹配商品名与件单价，返回命中的利润率规则。"""
        for rule in self.profit_rules:
            if rule.matches(product_name, unit_price_cny=unit_price_cny):
                return rule
        return None

    def get_profit_margin(
        self,
        product_name: str,
        *,
        unit_price_cny: Decimal | None = None,
    ) -> Decimal:
        """按规则顺序匹配商品名与件单价，返回利润率。"""
        rule = self.get_matching_profit_rule(product_name, unit_price_cny=unit_price_cny)
        if rule is not None:
            return rule.margin
        return self.default_profit_margin

    def get_low_margin_review_rules(
        self,
        product_name: str,
        *,
        unit_price_cny: Decimal | None = None,
    ) -> list[tuple[ProfitRule, str]]:
        """返回命中关键词但因阈值未生效的低毛利规则。"""
        reviews: list[tuple[ProfitRule, str]] = []
        for rule in self.profit_rules:
            reason = rule.get_skip_reason(product_name, unit_price_cny=unit_price_cny)
            if reason is not None:
                reviews.append((rule, reason))
        return reviews


def load_config(config_path: str | Path) -> AppConfig:
    """从 TOML 文件加载配置。"""
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"配置文件不存在: {path}")

    with open(path, "rb") as f:
        data = tomllib.load(f)

    pm = data.get("profit_margins", {})
    default_margin = Decimal(str(pm.get("default", 0.30)))

    rules: list[ProfitRule] = []
    for rule_data in pm.get("rules", []):
        rules.append(
            ProfitRule(
                pattern=rule_data["pattern"],
                margin=Decimal(str(rule_data["margin"])),
                description=rule_data.get("description", ""),
                max_unit_price_cny=(
                    Decimal(str(rule_data["max_unit_price_cny"]))
                    if "max_unit_price_cny" in rule_data
                    else None
                ),
            )
        )

    accounts: dict[str, AccountInfo] = {}
    for name, info in data.get("accounts", {}).items():
        accounts[name] = AccountInfo(
            region=info["region"],
            manager=info["manager"],
        )

    manager_monthly_gmv_usd: dict[str, dict[str, Decimal]] = {}
    for report_month, managers in data.get("manager_monthly_gmv_usd", {}).items():
        manager_monthly_gmv_usd[report_month] = {
            manager: Decimal(str(gmv_usd)) for manager, gmv_usd in managers.items()
        }

    return AppConfig(
        default_profit_margin=default_margin,
        profit_rules=rules,
        accounts=accounts,
        manager_monthly_gmv_usd=manager_monthly_gmv_usd,
    )
