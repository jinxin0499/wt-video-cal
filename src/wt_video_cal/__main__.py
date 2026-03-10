"""入口: python -m wt_video_cal"""

import logging
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from wt_video_cal import settings
from wt_video_cal.aggregator import aggregate
from wt_video_cal.calculator import calculate_all
from wt_video_cal.config import AppConfig, load_config
from wt_video_cal.excel_reader import read_all_excel_files
from wt_video_cal.excel_writer import write_all_reports
from wt_video_cal.exceptions import DuplicateVideoError, WtVideoCalError
from wt_video_cal.models import VideoRecord

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _fmt(value: Decimal) -> str:
    return f"{value:,.2f}"


def _filter_bound_accounts(
    records: list[VideoRecord], config: AppConfig
) -> list[VideoRecord]:
    """只保留配置中已绑定账号的记录，未绑定的达人警告并忽略。"""
    bound: list[VideoRecord] = []
    unbound_counts: dict[str, int] = defaultdict(int)

    for r in records:
        if config.get_account_info(r.creator_name) is not None:
            bound.append(r)
        else:
            unbound_counts[r.creator_name] += 1

    if unbound_counts:
        total_ignored = sum(unbound_counts.values())
        top_creators = sorted(unbound_counts.items(), key=lambda x: -x[1])[:10]
        preview = ", ".join(f"{name}({cnt}条)" for name, cnt in top_creators)
        more = f" ...等共{len(unbound_counts)}个达人" if len(unbound_counts) > 10 else ""
        logger.warning(
            "忽略 %d 条未绑定账号的记录: %s%s",
            total_ignored,
            preview,
            more,
        )

    logger.info("已绑定账号记录: %d 条（过滤前 %d 条）", len(bound), len(records))
    return bound


def _check_bound_duplicates(records: list[VideoRecord]) -> None:
    """仅在同一视频跨多个文件且每个文件都有转化订单时阻断。"""
    seen: dict[tuple[str, str], list[VideoRecord]] = defaultdict(list)
    for r in records:
        seen[(r.creator_name, r.video_id)].append(r)

    duplicates = [
        (
            creator,
            vid,
            sorted(file_orders.items()),
        )
        for (creator, vid), group_records in seen.items()
        for file_orders in [
            {
                file_path: sum(
                    record.orders
                    for record in group_records
                    if record.source_file == file_path
                )
                for file_path in {record.source_file for record in group_records}
            }
        ]
        if len(file_orders) > 1 and all(orders > 0 for orders in file_orders.values())
    ]

    if duplicates:
        raise DuplicateVideoError(duplicates)


def _build_source_file_summary(
    records: list[VideoRecord],
) -> dict[str, dict[str, dict[str, object]]]:
    """按来源文件 → 达人汇总绑定账号的原始数据，用于数据校验。

    返回: {文件名: {达人: {orders, items_sold, gmv, currency}}}
    """
    file_creator_stats: dict[str, dict[str, dict[str, object]]] = defaultdict(
        lambda: defaultdict(lambda: {"orders": 0, "items_sold": 0, "gmv": Decimal("0"), "currency": ""})
    )
    for r in records:
        fname = Path(r.source_file).name
        stats = file_creator_stats[fname][r.creator_name]
        stats["orders"] += r.orders
        stats["items_sold"] += r.items_sold
        stats["gmv"] += r.attributed_gmv
        stats["currency"] = r.currency.value
    return dict(file_creator_stats)


def _print_source_file_summary(
    summary: dict[str, dict[str, dict[str, object]]],
) -> None:
    """在控制台打印数据校验汇总。"""
    print("\n" + "-" * 60)
    print("  数据校验 — 绑定账号原始数据汇总")
    print("-" * 60)

    grand_orders = 0
    grand_items = 0
    grand_gmv = Decimal("0")

    for fname in sorted(summary):
        creators = summary[fname]
        file_orders = sum(s["orders"] for s in creators.values())
        file_items = sum(s["items_sold"] for s in creators.values())
        file_gmv = sum(s["gmv"] for s in creators.values())
        currency = next(iter(creators.values()))["currency"]

        print(f"\n  来源: {fname}")
        print(f"    绑定达人数: {len(creators)}, 订单: {file_orders}, "
              f"件数: {file_items}, GMV({currency}): {_fmt(file_gmv)}")

        for creator in sorted(creators):
            s = creators[creator]
            print(f"      {creator}: 订单={s['orders']}, "
                  f"件数={s['items_sold']}, GMV={_fmt(s['gmv'])}")

        grand_orders += file_orders
        grand_items += file_items
        grand_gmv += file_gmv

    print(f"\n  合计: 订单={grand_orders}, 件数={grand_items}, GMV={_fmt(grand_gmv)}")
    print("-" * 60)


def main() -> None:
    logger.info("=== 短视频团队提成计算 ===")
    logger.info("统计月份: %s", settings.REPORT_MONTH)
    logger.info(
        "美元汇率: %s, 英镑汇率: %s", settings.EXCHANGE_RATE_USD, settings.EXCHANGE_RATE_GBP
    )
    logger.info("提成比例: %s%%", settings.COMMISSION_RATE * 100)

    # 1. 加载配置
    logger.info("加载配置: %s", settings.CONFIG_PATH)
    config = load_config(settings.CONFIG_PATH)
    logger.info(
        "已加载 %d 个账号映射, %d 条利润率规则", len(config.accounts), len(config.profit_rules)
    )

    # 2. 读取 Excel（格式不匹配会抛异常中断）
    logger.info("读取输入目录: %s", settings.INPUT_DIR)
    all_records = read_all_excel_files(settings.INPUT_DIR)

    if not all_records:
        logger.warning("未读取到任何视频记录，请检查输入目录")
        return

    logger.info("共读取 %d 条视频记录", len(all_records))

    # 3. 过滤：只保留配置中已绑定账号的记录
    records = _filter_bound_accounts(all_records, config)

    if not records:
        logger.warning("过滤后无有效记录（所有达人均未在配置中绑定）")
        return

    # 4. 重复检测：仅针对已绑定账号的记录
    _check_bound_duplicates(records)

    # 5. 构建数据校验汇总
    source_summary = _build_source_file_summary(records)
    _print_source_file_summary(source_summary)

    # 6. 计算提成
    results = calculate_all(
        records,
        config,
        exchange_rate_usd=settings.EXCHANGE_RATE_USD,
        exchange_rate_gbp=settings.EXCHANGE_RATE_GBP,
        commission_rate=settings.COMMISSION_RATE,
    )

    # 7. 汇总
    managers = aggregate(results)

    # 8. 输出报表（含数据校验sheet）
    paths = write_all_reports(
        managers, settings.OUTPUT_DIR, settings.REPORT_MONTH,
        source_summary=source_summary,
    )
    logger.info("已生成 %d 个报表文件", len(paths))

    # 9. 控制台打印汇总
    print("\n" + "=" * 60)
    print(f"  提成汇总 — {settings.REPORT_MONTH}")
    print("=" * 60)

    total_commission = Decimal("0")
    for ms in sorted(managers.values(), key=lambda m: m.manager):
        print(f"\n  {ms.manager}:")
        print(f"    订单数: {ms.total_orders}  成交件数: {ms.total_items_sold}")
        print(f"    GMV(CNY): {_fmt(ms.total_gmv_cny)}")
        print(f"    提成(CNY): {_fmt(ms.total_commission)}")
        total_commission += ms.total_commission

        for acct in sorted(ms.accounts.values(), key=lambda a: a.account):
            print(f"      [{acct.account}] {acct.region} "
                  f"订单:{acct.total_orders} "
                  f"GMV(CNY):{_fmt(acct.total_gmv_cny)} "
                  f"提成:{_fmt(acct.total_commission)}")

    print(f"\n  总提成: {_fmt(total_commission)}")
    print("=" * 60)

    print("\n输出文件:")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    try:
        main()
    except WtVideoCalError as e:
        logger.error(str(e))
        sys.exit(1)
