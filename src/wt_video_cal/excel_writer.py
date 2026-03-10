import logging
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from wt_video_cal.models import AccountSummary, ManagerSummary
from wt_video_cal.settings import REPORT_MONTH

logger = logging.getLogger(__name__)

_HEADER_FONT = Font(bold=True)
_HEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
_TOTAL_FONT = Font(bold=True, color="C00000")
_TOTAL_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
_ALIGN_RIGHT = Alignment(horizontal="right")
_ALIGN_CENTER = Alignment(horizontal="center")


def _fmt(value: Decimal) -> float:
    """Decimal → float for Excel cell (保留2位精度)。"""
    return float(value.quantize(Decimal("0.01")))


def _fmt4(value: Decimal) -> float:
    """Decimal → float for Excel cell (保留4位精度，用于汇率)。"""
    return float(value.quantize(Decimal("0.0001")))


def _style_header(ws: object, row: int, col_count: int) -> None:
    """为表头行设置样式。"""
    for col in range(1, col_count + 1):
        cell = ws.cell(row=row, column=col)  # type: ignore[union-attr]
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _ALIGN_CENTER


def _auto_width(ws: object, col_count: int) -> None:
    """自动调整列宽。"""
    for col in range(1, col_count + 1):
        max_len = 0
        letter = get_column_letter(col)
        for row in ws.iter_rows(min_col=col, max_col=col, values_only=False):  # type: ignore[union-attr]
            for cell in row:
                if cell.value is not None:
                    # 中文字符按2倍宽度
                    val_str = str(cell.value)
                    char_len = sum(2 if ord(c) > 127 else 1 for c in val_str)
                    max_len = max(max_len, char_len)
        ws.column_dimensions[letter].width = min(max_len + 4, 50)  # type: ignore[union-attr]


def _write_summary_row(ws: object, row: int, col_count: int, values: list[object]) -> None:
    """写入合计行并设置样式。"""
    for col, val in enumerate(values, 1):
        cell = ws.cell(row=row, column=col)  # type: ignore[union-attr]
        cell.value = val
        cell.font = _TOTAL_FONT
        cell.fill = _TOTAL_FILL


def _get_account_currency_info(
    acct: AccountSummary,
) -> tuple[str, Decimal, Decimal]:
    """从明细记录中提取账号的币种、汇率、原币种GMV合计。

    若账号含多币种记录，以GMV较大的币种为主，币种标记加"*"。
    """
    currency_gmv: dict[str, Decimal] = defaultdict(Decimal)
    currency_rate: dict[str, Decimal] = {}
    for d in acct.details:
        cur = d.record.currency.value
        currency_gmv[cur] += d.record.attributed_gmv
        currency_rate[cur] = d.exchange_rate

    if len(currency_gmv) == 0:
        return "", Decimal("0"), Decimal("0")

    if len(currency_gmv) == 1:
        cur = next(iter(currency_gmv))
        return cur, currency_rate[cur], currency_gmv[cur]

    # 多币种：按GMV金额取主币种，标记"*"
    primary = max(currency_gmv, key=lambda c: currency_gmv[c])
    return primary + "*", currency_rate[primary], sum(currency_gmv.values())


def write_manager_report(
    manager_summary: ManagerSummary,
    output_dir: Path,
    report_month: str = REPORT_MONTH,
) -> Path:
    """为单位负责人生成提成明细报表。"""
    wb = Workbook()

    # === Sheet 1: 汇总 ===
    ws_summary = wb.active
    ws_summary.title = "汇总"  # type: ignore[union-attr]

    summary_headers = [
        "账号", "区域", "订单数", "成交件数",
        "GMV(原币种)", "币种", "汇率", "GMV(CNY)", "提成(CNY)",
    ]
    ws_summary.append(summary_headers)  # type: ignore[union-attr]
    _style_header(ws_summary, 1, len(summary_headers))

    row_num = 2
    for acct in sorted(manager_summary.accounts.values(), key=lambda a: a.account):
        currency, exchange_rate, gmv_original = _get_account_currency_info(acct)
        ws_summary.append([  # type: ignore[union-attr]
            acct.account,
            acct.region,
            acct.total_orders,
            acct.total_items_sold,
            _fmt(gmv_original),
            currency,
            _fmt4(exchange_rate),
            _fmt(acct.total_gmv_cny),
            _fmt(acct.total_commission),
        ])
        row_num += 1

    # 合计行
    _write_summary_row(ws_summary, row_num, len(summary_headers), [
        "合计", "",
        manager_summary.total_orders,
        manager_summary.total_items_sold,
        "", "", "",
        _fmt(manager_summary.total_gmv_cny),
        _fmt(manager_summary.total_commission),
    ])

    _auto_width(ws_summary, len(summary_headers))

    # === Sheet 2: 明细 ===
    ws_detail = wb.create_sheet("明细")
    detail_headers = [
        "账号", "视频ID", "商品",
        "订单数", "商品件数", "GMV(原币种)", "币种",
        "汇率", "GMV(CNY)", "利润率", "提成(CNY)",
    ]
    ws_detail.append(detail_headers)
    _style_header(ws_detail, 1, len(detail_headers))

    for acct in sorted(manager_summary.accounts.values(), key=lambda a: a.account):
        for detail in acct.details:
            ws_detail.append([
                detail.account,
                detail.record.video_id,
                detail.record.product_name,
                detail.record.orders,
                detail.record.items_sold,
                _fmt(detail.record.attributed_gmv),
                detail.record.currency.value,
                _fmt4(detail.exchange_rate),
                _fmt(detail.gmv_cny),
                f"{_fmt(detail.profit_margin * 100)}%",
                _fmt(detail.commission),
            ])

    _auto_width(ws_detail, len(detail_headers))

    # 保存
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{manager_summary.manager}_提成明细_{report_month}.xlsx"
    output_path = output_dir / filename
    wb.save(output_path)
    logger.info("已生成: %s", output_path)
    return output_path


def write_overview_report(
    managers: dict[str, ManagerSummary],
    output_dir: Path,
    report_month: str = REPORT_MONTH,
    source_summary: dict[str, dict[str, dict[str, object]]] | None = None,
) -> Path:
    """生成总览报表。"""
    wb = Workbook()

    # === Sheet 1: 负责人汇总 ===
    ws_managers = wb.active
    ws_managers.title = "负责人汇总"  # type: ignore[union-attr]

    mgr_headers = ["负责人", "订单数", "成交件数", "GMV(CNY)", "提成(CNY)"]
    ws_managers.append(mgr_headers)  # type: ignore[union-attr]
    _style_header(ws_managers, 1, len(mgr_headers))

    total_orders = 0
    total_items = 0
    total_gmv = Decimal("0")
    total_commission = Decimal("0")

    row_num = 2
    for ms in sorted(managers.values(), key=lambda m: m.manager):
        ws_managers.append([  # type: ignore[union-attr]
            ms.manager,
            ms.total_orders,
            ms.total_items_sold,
            _fmt(ms.total_gmv_cny),
            _fmt(ms.total_commission),
        ])
        total_orders += ms.total_orders
        total_items += ms.total_items_sold
        total_gmv += ms.total_gmv_cny
        total_commission += ms.total_commission
        row_num += 1

    _write_summary_row(ws_managers, row_num, len(mgr_headers), [
        "合计",
        total_orders,
        total_items,
        _fmt(total_gmv),
        _fmt(total_commission),
    ])

    _auto_width(ws_managers, len(mgr_headers))

    # === Sheet 2: 账号明细 ===
    ws_accounts = wb.create_sheet("账号明细")
    acct_headers = [
        "负责人", "账号", "区域", "订单数", "成交件数",
        "GMV(原币种)", "币种", "汇率", "GMV(CNY)", "提成(CNY)",
    ]
    ws_accounts.append(acct_headers)
    _style_header(ws_accounts, 1, len(acct_headers))

    for ms in sorted(managers.values(), key=lambda m: m.manager):
        for acct in sorted(ms.accounts.values(), key=lambda a: a.account):
            currency, exchange_rate, gmv_original = _get_account_currency_info(acct)
            ws_accounts.append([
                ms.manager,
                acct.account,
                acct.region,
                acct.total_orders,
                acct.total_items_sold,
                _fmt(gmv_original),
                currency,
                _fmt4(exchange_rate),
                _fmt(acct.total_gmv_cny),
                _fmt(acct.total_commission),
            ])

    _auto_width(ws_accounts, len(acct_headers))

    # === Sheet 3: 数据校验（按来源文件汇总绑定账号原始数据） ===
    if source_summary:
        ws_verify = wb.create_sheet("数据校验")
        verify_headers = ["来源文件", "达人", "订单数", "成交件数", "GMV", "币种"]
        ws_verify.append(verify_headers)
        _style_header(ws_verify, 1, len(verify_headers))

        grand_orders = 0
        grand_items = 0
        grand_gmv = Decimal("0")

        for fname in sorted(source_summary):
            creators = source_summary[fname]
            for creator in sorted(creators):
                s = creators[creator]
                ws_verify.append([
                    fname,
                    creator,
                    s["orders"],
                    s["items_sold"],
                    _fmt(s["gmv"]),
                    s["currency"],
                ])

            # 文件小计
            file_orders = sum(s["orders"] for s in creators.values())
            file_items = sum(s["items_sold"] for s in creators.values())
            file_gmv = sum(s["gmv"] for s in creators.values())
            row_num = ws_verify.max_row + 1
            _write_summary_row(ws_verify, row_num, len(verify_headers), [
                f"小计: {fname}", "",
                file_orders, file_items, _fmt(file_gmv), "",
            ])
            grand_orders += file_orders
            grand_items += file_items
            grand_gmv += file_gmv

        # 总合计
        row_num = ws_verify.max_row + 1
        _write_summary_row(ws_verify, row_num, len(verify_headers), [
            "合计", "",
            grand_orders, grand_items, _fmt(grand_gmv), "",
        ])

        _auto_width(ws_verify, len(verify_headers))

    # 保存
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"提成汇总_{report_month}.xlsx"
    output_path = output_dir / filename
    wb.save(output_path)
    logger.info("已生成: %s", output_path)
    return output_path


def write_all_reports(
    managers: dict[str, ManagerSummary],
    output_dir: str | Path,
    report_month: str = REPORT_MONTH,
    source_summary: dict[str, dict[str, dict[str, object]]] | None = None,
) -> list[Path]:
    """生成所有报表：总览 + 每位负责人明细。"""
    out = Path(output_dir)
    paths: list[Path] = []

    # 总览
    paths.append(write_overview_report(managers, out, report_month, source_summary))

    # 每位负责人
    for ms in managers.values():
        paths.append(write_manager_report(ms, out, report_month))

    return paths
