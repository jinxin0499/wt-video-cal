import tomllib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from wt_video_cal.exceptions import ConfigError


@dataclass(frozen=True)
class ProfitRule:
    pattern: str
    margin: Decimal
    description: str


@dataclass(frozen=True)
class AccountInfo:
    region: str
    manager: str


@dataclass(frozen=True)
class AppConfig:
    default_profit_margin: Decimal
    profit_rules: list[ProfitRule]
    accounts: dict[str, AccountInfo]

    def get_account_info(self, account_name: str) -> AccountInfo | None:
        """大小写不敏感地查找账号信息。"""
        lower = account_name.lower()
        for key, info in self.accounts.items():
            if key.lower() == lower:
                return info
        return None

    def get_profit_margin(self, product_name: str) -> Decimal:
        """按规则顺序匹配商品名（子串匹配，大小写不敏感），返回利润率。"""
        product_lower = product_name.lower()
        for rule in self.profit_rules:
            if rule.pattern.lower() in product_lower:
                return rule.margin
        return self.default_profit_margin


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
            )
        )

    accounts: dict[str, AccountInfo] = {}
    for name, info in data.get("accounts", {}).items():
        accounts[name] = AccountInfo(
            region=info["region"],
            manager=info["manager"],
        )

    return AppConfig(
        default_profit_margin=default_margin,
        profit_rules=rules,
        accounts=accounts,
    )
