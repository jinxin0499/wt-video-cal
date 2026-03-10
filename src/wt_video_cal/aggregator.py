from wt_video_cal.models import AccountSummary, CommissionResult, ManagerSummary


def aggregate(results: list[CommissionResult]) -> dict[str, ManagerSummary]:
    """按 负责人 → 账号 两级分组汇总。"""
    managers: dict[str, ManagerSummary] = {}

    for r in results:
        # 获取或创建 ManagerSummary
        if r.manager not in managers:
            managers[r.manager] = ManagerSummary(manager=r.manager)
        ms = managers[r.manager]

        # 获取或创建 AccountSummary
        if r.account not in ms.accounts:
            ms.accounts[r.account] = AccountSummary(
                account=r.account,
                region=r.region,
                manager=r.manager,
            )
        acct = ms.accounts[r.account]

        # 累加账号级别
        acct.total_orders += r.record.orders
        acct.total_items_sold += r.record.items_sold
        acct.total_gmv_cny += r.gmv_cny
        acct.total_profit_cny += r.profit_cny
        acct.total_commission += r.commission
        acct.details.append(r)

        # 累加负责人级别
        ms.total_orders += r.record.orders
        ms.total_items_sold += r.record.items_sold
        ms.total_gmv_cny += r.gmv_cny
        ms.total_profit_cny += r.profit_cny
        ms.total_commission += r.commission

    return managers
