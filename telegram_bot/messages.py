from html import escape
from typing import Any, Dict, List
from datetime import datetime


def _es(text: str | float | int | None) -> str:
    return escape(str(text or ""))


def _fmt_pnl(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}${value:,.2f}"


def _fmt_pnl_pct(value: float, base: float) -> str:
    if abs(base) < 0.01:
        return "0.00%"
    pct = (value / base) * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"


def _risk_emoji(level: str) -> str:
    mapping = {"low": "🟢", "moderate": "🟡", "elevated": "🟠", "high": "🔴", "critical": "🚨"}
    return mapping.get(level.lower(), "⚪")


def _health_emoji(score: float) -> str:
    if score >= 70:
        return "🟢"
    if score >= 40:
        return "🟡"
    return "🔴"


SEP = "━" * 20


def format_portfolio_summary(data: Dict[str, Any]) -> str:
    tv = data.get("total_value", 0)
    dpnl = data.get("daily_pnl", 0)
    wpnl = data.get("weekly_pnl", 0)
    mpnl = data.get("monthly_pnl", 0)
    health = data.get("health_score", 100)
    risk = data.get("risk_level", "moderate")
    upnl = data.get("unrealized_pnl", 0)
    upnl_pct = data.get("unrealized_pnl_percent", 0)
    positions = data.get("total_positions", 0)
    traders = data.get("active_traders", 0)
    total_traders = data.get("total_traders", 0)
    cash = data.get("cash_balance", 0)
    invested = data.get("invested_amount", 0)

    daily_pct = (dpnl / (tv - dpnl)) * 100 if (tv - dpnl) > 0 else 0
    daily_sign = "+" if dpnl >= 0 else ""
    weekly_sign = "+" if wpnl >= 0 else ""
    monthly_sign = "+" if mpnl >= 0 else ""
    upnl_sign = "+" if upnl >= 0 else ""

    lines = [
        "📊 <b>Portfolio Summary</b>",
        SEP,
        f"• <b>Total Value:</b> <code>${_es(f'{tv:,.2f}')}</code>",
        f"• <b>Daily PnL:</b> <code>{daily_sign}${_es(f'{dpnl:,.2f}')}</code> (<code>{daily_sign}{_es(f'{daily_pct:.2f}')}%</code>)",
        f"• <b>Weekly PnL:</b> <code>{weekly_sign}${_es(f'{wpnl:,.2f}')}</code>",
        f"• <b>Monthly PnL:</b> <code>{monthly_sign}${_es(f'{mpnl:,.2f}')}</code>",
        f"• <b>Health Score:</b> <code>{_es(f'{health:.0f}')}/100</code> {_health_emoji(health)}",
        f"• <b>Risk Level:</b> {_risk_emoji(risk)} <code>{_es(risk.title())}</code>",
        SEP,
        f"<b>Positions:</b> <code>{positions}</code> | <b>Traders:</b> <code>{traders}/{total_traders}</code>",
        f"<b>Cash:</b> <code>${_es(f'{cash:,.2f}')}</code> | <b>Invested:</b> <code>${_es(f'{invested:,.2f}')}</code>",
        f"<b>Unrealized PnL:</b> <code>{upnl_sign}${_es(f'{upnl:,.2f}')}</code> (<code>{upnl_sign}{_es(f'{upnl_pct:.2f}')}%</code>)",
    ]
    return "\n".join(lines)


def format_risk_alert(alert: Dict[str, Any]) -> str:
    title = alert.get("title", "Risk Alert")
    message = alert.get("message", "")
    severity = alert.get("severity", "info")
    url = alert.get("url", "")
    created = alert.get("created_at", "")

    sev_icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
    icon = sev_icon.get(severity, "ℹ️")

    lines = [
        f"{icon} <b>Risk Alert: {_es(title)}</b>",
        SEP,
        _es(message),
    ]
    if url:
        lines.append(f"\n<b>URL:</b> {_es(url)}")
    if created:
        if isinstance(created, datetime):
            created = created.strftime("%b %d, %H:%M")
        lines.append(f"<b>Time:</b> {_es(created)}")
    lines.append(f"<b>Severity:</b> <code>{_es(severity.upper())}</code>")
    return "\n".join(lines)


def format_trader_list(traders: List[Dict[str, Any]]) -> str:
    if not traders:
        return "📭 <b>No copied traders found.</b>"

    lines = ["📋 <b>Copied Traders</b>", SEP]
    for t in traders:
        name = t.get("trader_name", "Unknown")
        status = t.get("status", "unknown")
        classification = t.get("classification", "unknown")
        alloc = t.get("allocation_percent", 0)
        pnl = t.get("total_pnl", 0)
        roi = t.get("total_roi", 0)

        status_icon = "🟢" if status == "active" else "⏸️" if status == "paused" else "🔴"
        pnl_sign = "+" if pnl >= 0 else ""
        roi_sign = "+" if roi >= 0 else ""

        lines.append(
            f"{status_icon} <b>{_es(name)}</b>\n"
            f"   <code>{_es(classification.upper())}</code> | Alloc: <code>{_es(f'{alloc:.1f}')}%</code>\n"
            f"   PnL: <code>{pnl_sign}${_es(f'{pnl:,.2f}')}</code> | ROI: <code>{roi_sign}{_es(f'{roi:.2f}')}%</code>"
        )

    active = sum(1 for t in traders if t.get("status") == "active")
    lines.append(f"\n<b>Total:</b> {len(traders)} | <b>Active:</b> {active}")
    return "\n".join(lines)


def format_trader_detail(trader: Dict[str, Any], analysis: Dict[str, Any] | None) -> str:
    name = trader.get("trader_name", "Unknown")
    status = trader.get("status", "unknown")
    classification = trader.get("classification", analysis.get("classification", "unknown")) if analysis else trader.get("classification", "unknown")
    alloc = trader.get("allocation_percent", 0)
    current_value = trader.get("current_value", 0)
    total_pnl = trader.get("total_pnl", 0)
    total_roi = trader.get("total_roi", 0)
    copied_at = trader.get("copied_at", "")
    last_updated = trader.get("last_updated", "")

    status_icon = "🟢" if status == "active" else "⏸️" if status == "paused" else "🔴"
    pnl_sign = "+" if total_pnl >= 0 else ""
    roi_sign = "+" if total_roi >= 0 else ""

    if isinstance(copied_at, datetime):
        copied_at = copied_at.strftime("%b %d, %Y")
    if isinstance(last_updated, datetime):
        last_updated = last_updated.strftime("%b %d, %H:%M")

    lines = [
        f"{status_icon} <b>Trader: {_es(name)}</b>",
        SEP,
        f"• <b>Status:</b> <code>{_es(status.upper())}</code>",
        f"• <b>Classification:</b> {_risk_emoji(classification)} <code>{_es(classification.upper())}</code>",
        f"• <b>Allocation:</b> <code>{_es(f'{alloc:.1f}')}%</code>",
        f"• <b>Current Value:</b> <code>${_es(f'{current_value:,.2f}')}</code>",
        f"• <b>Total PnL:</b> <code>{pnl_sign}${_es(f'{total_pnl:,.2f}')}</code>",
        f"• <b>Total ROI:</b> <code>{roi_sign}{_es(f'{total_roi:.2f}')}%</code>",
    ]
    if copied_at:
        lines.append(f"• <b>Copied:</b> {_es(copied_at)}")
    if last_updated:
        lines.append(f"• <b>Updated:</b> {_es(last_updated)}")

    if analysis:
        trend = analysis.get("performance_trend", "stable")
        reason = analysis.get("classification_reason", "")
        rec = analysis.get("recommendation", "")
        risk = analysis.get("risk_metrics", {})

        trend_icon = {"improving": "📈", "declining": "📉", "stable": "➡️", "insufficient_data": "❓"}
        lines.extend([
            "",
            f"<b>Analysis</b>",
            SEP,
            f"• <b>Trend:</b> {trend_icon.get(trend, '➡️')} <code>{_es(trend)}</code>",
        ])
        if reason:
            lines.append(f"• <b>Reason:</b> {_es(reason)}")
        avg_monthly = risk.get("avg_monthly_return")
        if avg_monthly is not None:
            lines.append(f"• <b>Avg Monthly Return:</b> <code>{_es(f'{avg_monthly:.2f}')}%</code>")
        avg_vol = risk.get("avg_volatility")
        if avg_vol is not None:
            lines.append(f"• <b>Volatility:</b> <code>{_es(f'{avg_vol:.2f}')}%</code>")
        max_dd = risk.get("max_drawdown")
        if max_dd is not None:
            lines.append(f"• <b>Max Drawdown:</b> <code>{_es(f'{max_dd:.2f}')}%</code>")
        win_rate = risk.get("avg_win_rate")
        if win_rate is not None:
            lines.append(f"• <b>Win Rate:</b> <code>{_es(f'{win_rate:.1f}')}%</code>")
        consistency = risk.get("consistency_score")
        if consistency is not None:
            lines.append(f"• <b>Consistency:</b> <code>{_es(f'{consistency:.1f}')}/100</code>")
        sharpe = risk.get("sharpe_like_score")
        if sharpe is not None:
            lines.append(f"• <b>Sharpe-like:</b> <code>{_es(f'{sharpe:.2f}')}</code>")
        if rec:
            lines.extend(["", f"💡 <b>Recommendation:</b> {_es(rec)}"])

    return "\n".join(lines)


def format_performance_summary(metrics: Dict[str, Any]) -> str:
    period = metrics.get("period", "1m")
    total_return = metrics.get("total_return", 0)
    start_value = metrics.get("start_value", 0)
    end_value = metrics.get("end_value", 0)
    ann_return = metrics.get("annualized_return", 0)
    best = metrics.get("best_month", {})
    worst = metrics.get("worst_month", {})
    pos_pct = metrics.get("percent_positive_months", 0)
    ulcer = metrics.get("ulcer_index", 0)

    ret_sign = "+" if total_return >= 0 else ""
    ann_sign = "+" if ann_return >= 0 else ""

    vol = 0
    summary = metrics.get("summary", {})
    if isinstance(summary, dict):
        vol = summary.get("volatility", 0)
        vol_text = summary.get("volatility", "")

    perf_icon = "📈" if total_return >= 0 else "📉"
    best_ret = best.get("return", 0) if isinstance(best, dict) else 0
    worst_ret = worst.get("return", 0) if isinstance(worst, dict) else 0
    best_sign = "+" if best_ret >= 0 else ""
    worst_sign = "" if worst_ret >= 0 else "-"

    lines = [
        f"{perf_icon} <b>Performance Summary</b>",
        SEP,
        f"• <b>Period:</b> <code>{_es(period.upper())}</code>",
        f"• <b>Total Return:</b> <code>{ret_sign}{_es(f'{total_return:.2f}')}%</code>",
        f"• <b>Start Value:</b> <code>${_es(f'{start_value:,.2f}')}</code> → <b>End:</b> <code>${_es(f'{end_value:,.2f}')}</code>",
        f"• <b>Annualized Return:</b> <code>{ann_sign}{_es(f'{ann_return:.2f}')}%</code>",
        SEP,
        f"📅 <b>Best Month:</b> <code>{best_sign}{_es(f'{best_ret:.2f}')}%</code>",
        f"📅 <b>Worst Month:</b> <code>{worst_sign}{_es(f'{abs(worst_ret):.2f}')}%</code>",
        f"✅ <b>Positive Months:</b> <code>{_es(f'{pos_pct:.1f}')}%</code>",
        SEP,
    ]

    if isinstance(vol, (int, float)):
        vol_icon = "🟢" if vol < 0.15 else "🟡" if vol < 0.25 else "🔴"
        lines.append(f"{vol_icon} <b>Volatility:</b> <code>{_es(f'{vol*100:.2f}')}%</code>")

    ulcer_icon = "🟢" if ulcer < 5 else "🟡" if ulcer < 10 else "🔴"
    lines.append(f"{ulcer_icon} <b>Ulcer Index:</b> <code>{_es(f'{ulcer:.2f}')}</code>")

    return "\n".join(lines)


def format_ai_recommendation(rec: Dict[str, Any]) -> str:
    rectype = rec.get("recommendation_type", rec.get("type", "general"))
    title = rec.get("title", "Recommendation")
    summary = rec.get("summary", "")
    confidence = rec.get("confidence_score", 0)
    risk = rec.get("risk_impact", "medium")
    applied = rec.get("applied", False)
    source = rec.get("source", "ai")

    type_icons = {
        "reduce": "⬇️", "pause": "⏸️", "take_profit": "💰",
        "monitor": "👁️", "rebalance": "⚖️", "risk_alert": "🚨",
        "trader_review": "🔍", "portfolio_health": "✅",
        "general": "💡",
    }
    icon = type_icons.get(rectype, "💡")

    risk_icon = {"critical": "🚨", "high": "🔴", "medium": "🟡", "low": "🟢"}
    conf_stars = "⭐" * min(5, max(1, int(confidence * 5)))

    lines = [
        f"{icon} <b>AI Recommendation</b>",
        SEP,
        f"<b>{_es(title)}</b>",
        "",
        _es(summary),
        "",
        f"<b>Type:</b> <code>{_es(rectype)}</code> | <b>Source:</b> <code>{_es(source.upper())}</code>",
        f"<b>Confidence:</b> {conf_stars} <code>{_es(f'{confidence*100:.0f}')}%</code>",
        f"<b>Risk Impact:</b> {risk_icon.get(risk, '⚪')} <code>{_es(risk.upper())}</code>",
    ]
    if applied:
        lines.append("\n✅ <b>Applied</b>")
    return "\n".join(lines)


def format_weekly_summary(data: Dict[str, Any]) -> str:
    title = data.get("title", data.get("message", "Weekly Summary"))
    message = data.get("message", data.get("summary", ""))
    created = data.get("created_at", "")

    if isinstance(created, datetime):
        created = created.strftime("%b %d, %Y")

    lines = [
        "📅 <b>Weekly Portfolio Summary</b>",
        SEP,
        f"<b>{_es(title)}</b>" if title != "Weekly Summary" else "",
        "",
        _es(message),
    ]

    # Parse message lines for structured display
    msg_lines = message.split("\n") if message else []
    for ml in msg_lines:
        if "Portfolio Value:" in ml:
            continue
        if "Weekly PnL:" in ml:
            continue
        if "Health Score:" in ml:
            continue

    if isinstance(created, str) and created:
        lines.append(f"\n📅 {created}")
    return "\n".join(lines)


def format_alert_list(alerts: List[Dict[str, Any]]) -> str:
    if not alerts:
        return "✅ <b>No alerts.</b>"

    lines = ["🔔 <b>Recent Alerts</b>", SEP]

    for alert in alerts[:10]:
        alert_id = alert.get("id", "?")
        title = alert.get("title", "Alert")
        severity = alert.get("severity", "info")
        read = alert.get("read", False)
        created = alert.get("created_at", "")
        alert_type = alert.get("type", "")

        sev_icons = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
        icon = sev_icons.get(severity, "ℹ️")
        unread_mark = " 🔵" if not read else ""

        if isinstance(created, datetime):
            created = created.strftime("%b %d, %H:%M")

        lines.append(
            f"{icon}{unread_mark} <b>{_es(title)}</b>\n"
            f"   <code>{_es(severity.upper())}</code> | {_es(alert_type)} | {_es(created)}"
        )

    unread = sum(1 for a in alerts if not a.get("read", False))
    lines.append(f"\n<b>Total:</b> {len(alerts)} | <b>Unread:</b> {unread}")
    return "\n".join(lines)


def format_automation_action(action: Dict[str, Any]) -> str:
    action_type = action.get("action", action.get("type", "unknown"))
    status = action.get("status", "completed")
    details = action.get("details", {})

    icon = "✅" if status == "completed" else "❌" if status == "failed" else "⚠️"

    lines = [
        f"{icon} <b>Automation Action</b>",
        SEP,
        f"• <b>Action:</b> <code>{_es(action_type)}</code>",
        f"• <b>Status:</b> <code>{_es(status.upper())}</code>",
    ]
    if details:
        details_str = str(details)
        if len(details_str) > 200:
            details_str = details_str[:200] + "..."
        lines.append(f"• <b>Details:</b> <code>{_es(details_str)}</code>")
    return "\n".join(lines)


def format_error(message: str) -> str:
    return f"❌ <b>Error</b>\n{SEP}\n{_es(message)}"


def format_help() -> str:
    return (
        "🤖 <b>eToro Portfolio Bot - Help</b>\n"
        f"{SEP}\n"
        "<b>Portfolio</b>\n"
        "/status - Portfolio overview with PnL and health\n"
        "/portfolio - Detailed positions and allocation\n"
        "/performance - Performance metrics and returns\n\n"
        "<b>Traders</b>\n"
        "/traders - List all copied traders\n"
        "/traders &lt;name&gt; - Details for specific trader\n"
        "/pause &lt;name&gt; - Pause copy relationship\n"
        "/resume &lt;name&gt; - Resume copy relationship\n\n"
        "<b>Risk</b>\n"
        "/risk - Risk analysis and metrics\n"
        "/emergency - Emergency protection status\n"
        "/alerts - Recent portfolio alerts\n\n"
        "<b>AI &amp; Automation</b>\n"
        "/recommend - Get AI recommendations\n"
        "/analyze - Trigger full AI analysis\n\n"
        "<b>General</b>\n"
        "/start - Welcome message\n"
        "/help - Show this help"
    )
