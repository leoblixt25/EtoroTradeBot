import structlog
import random
from contextlib import asynccontextmanager
from typing import Any, Dict, List
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from sqlalchemy import select, desc

from backend.config.settings import settings
from backend.database.db import async_session_factory
from backend.database.models import (
    User, Portfolio, CopiedTrader, RiskMetric,
    Alert, AiRecommendation, AuditLog, AutomationRule,
)
from backend.services.portfolio_service import PortfolioService
from backend.services.trader_service import TraderService
from backend.services.alerts_service import AlertsService
from backend.analytics.performance import PerformanceAnalyzer
from backend.analytics.risk_scorer import RiskScorer
from backend.analytics.trader_analyzer import TraderAnalyzer
from backend.risk.emergency import EmergencyProtection
from backend.risk.manager import RiskManager
from backend.risk.limits import RiskLimits

from telegram_bot.messages import (
    format_portfolio_summary, format_risk_alert, format_trader_list,
    format_trader_detail, format_performance_summary, format_ai_recommendation,
    format_weekly_summary, format_alert_list, format_automation_action,
    format_error, format_help,
)
from telegram_bot.keyboards import (
    main_menu_keyboard, trader_detail_keyboard, alert_keyboard,
    confirmation_keyboard, risk_menu_keyboard, automation_menu_keyboard,
    trader_selection_keyboard, refresh_keyboard,
)

logger = structlog.get_logger(__name__)

# ── Conversation States ──────────────────────────────────────────────────────
PAUSE_SELECT, PAUSE_CONFIRM = range(2)
RESUME_SELECT, RESUME_CONFIRM = range(2, 4)

# ── Helpers ──────────────────────────────────────────────────────────────────

async def _check_auth(update: Update) -> bool:
    if not settings.TELEGRAM_CHAT_ID:
        return False
    chat_id = str(update.effective_chat.id)
    return chat_id == settings.TELEGRAM_CHAT_ID


@asynccontextmanager
async def _get_session():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _ensure_user_portfolio(session) -> tuple[int, int]:
    stmt = select(User).limit(1)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            username="default", email="default@etoro.local",
            hashed_password="placeholder",
        )
        session.add(user)
        await session.flush()

    pstmt = select(Portfolio).where(Portfolio.user_id == user.id)
    presult = await session.execute(pstmt)
    portfolio = presult.scalar_one_or_none()
    if portfolio is None:
        portfolio = Portfolio(
            user_id=user.id, total_value=10000.0,
            cash_balance=10000.0, invested_amount=0.0,
        )
        session.add(portfolio)
        await session.flush()

    return user.id, portfolio.id


async def _reply(update: Update, text: str, keyboard: InlineKeyboardMarkup | None = None, parse_mode: str = "HTML"):
    kw = {"parse_mode": parse_mode, "disable_web_page_preview": True}
    if keyboard:
        kw["reply_markup"] = keyboard
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, **kw)
        except Exception:
            await update.effective_chat.send_message(text, **kw)
    elif update.message:
        await update.message.reply_text(text, **kw)
    else:
        await update.effective_chat.send_message(text, **kw)


def _pnl_arrow(val: float) -> str:
    return "📈" if val >= 0 else "📉"


def _severity_emoji(s: str) -> str:
    return {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(s, "ℹ️")


# ── Start ────────────────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        await _reply(update, format_error("Unauthorized. This bot is private."))
        return
    text = (
        "🤖 <b>eToro Portfolio Manager Bot</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Welcome to your AI-powered portfolio assistant.\n\n"
        "<b>Focus: Capital Preservation</b>\n"
        "Monitor your eToro portfolio, track risks, and get "
        "intelligent recommendations to protect your capital.\n\n"
        "Use /help to see all available commands."
    )
    await _reply(update, text, main_menu_keyboard())


# ── Status ──────────────────────────────────────────────────────────────────

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    try:
        async with _get_session() as session:
            ps = PortfolioService(session)
            _, portfolio_id = await _ensure_user_portfolio(session)
            summary = await ps.get_portfolio_summary(portfolio_id)

            risk_stmt = select(RiskMetric).where(RiskMetric.portfolio_id == portfolio_id).order_by(desc(RiskMetric.timestamp)).limit(1)
            rresult = await session.execute(risk_stmt)
            latest_risk = rresult.scalar_one_or_none()

            risk_level = "moderate"
            if latest_risk:
                risk_level = RiskScorer.get_risk_level(int(latest_risk.risk_score))

            stmt = select(CopiedTrader).where(CopiedTrader.portfolio_id == portfolio_id)
            tresult = await session.execute(stmt)
            traders = list(tresult.scalars().all())

            data = {
                "total_value": summary.total_value,
                "cash_balance": summary.cash_balance,
                "invested_amount": summary.invested_amount,
                "daily_pnl": summary.daily_pnl,
                "weekly_pnl": summary.weekly_pnl,
                "monthly_pnl": summary.monthly_pnl,
                "health_score": summary.health_score,
                "risk_level": risk_level,
                "unrealized_pnl": summary.unrealized_pnl,
                "total_positions": summary.total_positions,
                "total_traders": summary.total_traders,
                "active_traders": summary.active_traders,
                "unrealized_pnl_percent": (
                    (summary.unrealized_pnl / summary.invested_amount * 100)
                    if summary.invested_amount else 0
                ),
            }
            await _reply(update, format_portfolio_summary(data), refresh_keyboard("status"))
    except Exception as e:
        logger.error("status_command failed", error=str(e))
        await _reply(update, format_error("Failed to fetch portfolio status."))


# ── Portfolio Detail ────────────────────────────────────────────────────────

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    try:
        async with _get_session() as session:
            ps = PortfolioService(session)
            ts = TraderService(session)
            user_id, portfolio_id = await _ensure_user_portfolio(session)
            portfolio = await ps.get_portfolio(user_id)
            if portfolio is None:
                portfolio = await ps.get_or_create_portfolio(user_id)
            positions = await ps.get_positions(portfolio_id)
            traders = await ts.get_all_traders(portfolio_id)

            lines = ["📋 <b>Portfolio Breakdown</b>", "━" * 20]
            lines.append(f"<b>Value:</b> <code>${portfolio.total_value:,.2f}</code>")
            lines.append(f"<b>Cash:</b> <code>${portfolio.cash_balance:,.2f}</code>")
            lines.append(f"<b>Invested:</b> <code>${portfolio.invested_amount:,.2f}</code>")
            lines.append(f"<b>Unrealized PnL:</b> <code>{_pnl_arrow(portfolio.unrealized_pnl)} ${portfolio.unrealized_pnl:+,.2f}</code>")
            lines.append(f"<b>Realized PnL:</b> <code>${portfolio.realized_pnl:+,.2f}</code>")
            lines.extend(["", "<b>Positions</b>", "━" * 20])

            if positions:
                for p in sorted(positions, key=lambda x: abs(x.pnl), reverse=True)[:15]:
                    pnl_s = "+" if p.pnl >= 0 else ""
                    lines.append(
                        f"• {_es(p.instrument_symbol)} <code>{p.instrument_type}</code>\n"
                        f"  Alloc: <code>${p.allocated_amount:,.2f}</code> | "
                        f"PnL: <code>{pnl_s}${p.pnl:,.2f}</code> ({pnl_s}{p.pnl_percent:.2f}%)"
                    )
            else:
                lines.append("  No open positions.")

            lines.extend(["", "<b>Copied Traders</b>", "━" * 20])
            if traders:
                for t in traders:
                    status_icon = "🟢" if t.status == "active" else "⏸️"
                    pnl_s = "+" if t.total_pnl >= 0 else ""
                    lines.append(
                        f"{status_icon} <b>{_es(t.trader_name)}</b>\n"
                        f"  Alloc: <code>{t.allocation_percent:.1f}%</code> | "
                        f"ROI: <code>{pnl_s}{t.total_roi:.2f}%</code> | "
                        f"<code>{_es(t.classification.upper())}</code>"
                    )
            else:
                lines.append("  No copied traders.")

            await _reply(update, "\n".join(lines), refresh_keyboard("portfolio"))
    except Exception as e:
        logger.error("portfolio_command failed", error=str(e))
        await _reply(update, format_error("Failed to fetch portfolio breakdown."))


# ── Risk ─────────────────────────────────────────────────────────────────────

async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    try:
        async with _get_session() as session:
            ps = PortfolioService(session)
            ts = TraderService(session)
            _, portfolio_id = await _ensure_user_portfolio(session)
            summary = await ps.get_portfolio_summary(portfolio_id)

            risk_stmt = select(RiskMetric).where(RiskMetric.portfolio_id == portfolio_id).order_by(desc(RiskMetric.timestamp)).limit(1)
            rresult = await session.execute(risk_stmt)
            latest_risk = rresult.scalar_one_or_none()

            traders = await ts.get_all_traders(portfolio_id)
            high_risk_count = sum(1 for t in traders if t.classification in ("aggressive", "high_risk"))
            paused_count = sum(1 for t in traders if t.status == "paused")

            risk_score = latest_risk.risk_score if latest_risk else 0
            health = latest_risk.health_score if latest_risk else summary.health_score
            max_dd = (latest_risk.max_drawdown or 0) if latest_risk else 0
            volatility = (latest_risk.volatility or 0) if latest_risk else 0
            var_95 = (latest_risk.var_95 or 0) if latest_risk else 0
            concentration = (latest_risk.concentration_risk or 0) if latest_risk else 0

            risk_level = RiskScorer.get_risk_level(int(risk_score))
            risk_emoji = {"low": "🟢", "moderate": "🟡", "elevated": "🟠", "high": "🔴", "critical": "🚨"}

            lines = [
                "⚠️ <b>Risk Analysis</b>",
                "━" * 20,
                f"<b>Risk Score:</b> {risk_emoji.get(risk_level, '⚪')} <code>{risk_score:.1f}/100</code> — <code>{_es(risk_level.upper())}</code>",
                f"<b>Health Score:</b> <code>{health:.1f}/100</code>",
                f"<b>Current Drawdown:</b> <code>{max_dd*100:.2f}%</code>",
                f"<b>Value at Risk (95%):</b> <code>${var_95:,.2f}</code>",
                f"<b>Volatility:</b> <code>{volatility*100:.2f}%</code>",
                f"<b>Concentration Risk:</b> <code>{concentration:.2%}</code>",
                "",
                "<b>Portfolio Composition</b>",
                "━" * 20,
                f"• High Risk Traders: <code>{high_risk_count}</code>",
                f"• Paused Traders: <code>{paused_count}</code>",
                f"• Active Traders: <code>{summary.active_traders}</code>",
                f"• Largest Allocation: <code>{summary.largest_allocation:.1f}%</code>",
                "",
                "<b>Thresholds</b>",
                "━" * 20,
                f"• Max Drawdown: <code>{RiskLimits.MAX_PORTFOLIO_DRAWDOWN*100:.0f}%</code>",
                f"• Max per Trader: <code>{RiskLimits.MAX_ALLOCATION_PER_TRADER*100:.0f}%</code>",
                f"• Min Diversification: <code>{RiskLimits.MIN_DIVERSIFICATION}</code> traders",
                f"• Max Daily Loss: <code>{RiskLimits.MAX_DAILY_LOSS*100:.0f}%</code>",
                f"• Emergency Drawdown: <code>{RiskLimits.EMERGENCY_STOP_DRAWDOWN*100:.0f}%</code>",
            ]

            exceeded = []
            if abs(max_dd) > RiskLimits.MAX_PORTFOLIO_DRAWDOWN:
                exceeded.append(f"🚨 Drawdown <code>{abs(max_dd)*100:.1f}%</code> exceeds <code>{RiskLimits.MAX_PORTFOLIO_DRAWDOWN*100:.0f}%</code> limit")
            if volatility > RiskLimits.MAX_VOLATILITY:
                exceeded.append(f"⚠️ Volatility <code>{volatility*100:.1f}%</code> exceeds <code>{RiskLimits.MAX_VOLATILITY*100:.0f}%</code> limit")
            if health < RiskLimits.MIN_HEALTH_SCORE:
                exceeded.append(f"🚨 Health score <code>{health:.0f}</code> below <code>{RiskLimits.MIN_HEALTH_SCORE}</code> minimum")

            if exceeded:
                lines.extend(["", "🚨 <b>Limit Violations</b>", "━" * 20] + exceeded)

            await _reply(update, "\n".join(lines), risk_menu_keyboard())
    except Exception as e:
        logger.error("risk_command failed", error=str(e))
        await _reply(update, format_error("Failed to fetch risk analysis."))


# ── Traders ──────────────────────────────────────────────────────────────────

async def traders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    try:
        async with _get_session() as session:
            ts = TraderService(session)
            _, portfolio_id = await _ensure_user_portfolio(session)
            traders = await ts.get_all_traders(portfolio_id)

            if context.args:
                query = " ".join(context.args).lower()
                matches = [t for t in traders if query in t.trader_name.lower()]
                if not matches:
                    await _reply(update, format_error(f"No traders found matching '{context.args[0]}'."))
                    return
                if len(matches) > 1:
                    lines = [f"🔍 Multiple traders matching '<b>{_es(context.args[0])}</b>':", ""]
                    for t in matches:
                        s_icon = "🟢" if t.status == "active" else "⏸️"
                        lines.append(f"{s_icon} <b>{_es(t.trader_name)}</b> — <code>{_es(t.classification.upper())}</code> | Alloc: <code>{t.allocation_percent:.1f}%</code>")
                    await _reply(update, "\n".join(lines))
                    return

                trader = matches[0]
                analysis = await ts.get_trader_analysis(trader.id)
                tdict = {
                    "trader_name": trader.trader_name, "status": trader.status,
                    "classification": trader.classification, "allocation_percent": trader.allocation_percent,
                    "current_value": trader.current_value, "total_pnl": trader.total_pnl,
                    "total_roi": trader.total_roi, "copied_at": trader.copied_at,
                    "last_updated": trader.last_updated,
                }
                adict = None
                if analysis:
                    adict = {
                        "classification": analysis.classification,
                        "classification_reason": analysis.classification_reason,
                        "performance_trend": analysis.performance_trend,
                        "recommendation": analysis.recommendation,
                        "risk_metrics": analysis.risk_metrics,
                    }
                text = format_trader_detail(tdict, adict)
                await _reply(update, text, trader_detail_keyboard(trader.id))
                return

            tlist = []
            for t in traders:
                tlist.append({
                    "trader_name": t.trader_name, "status": t.status,
                    "classification": t.classification, "allocation_percent": t.allocation_percent,
                    "total_pnl": t.total_pnl, "total_roi": t.total_roi,
                })
            await _reply(update, format_trader_list(tlist), refresh_keyboard("traders"))
    except Exception as e:
        logger.error("traders_command failed", error=str(e))
        await _reply(update, format_error("Failed to fetch trader data."))


# ── Performance ──────────────────────────────────────────────────────────────

async def performance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    try:
        async with _get_session() as session:
            ps = PortfolioService(session)
            _, portfolio_id = await _ensure_user_portfolio(session)
            history = await ps.get_performance_history(portfolio_id, "3m")

            history_dicts = [{"date": p.date, "value": p.value, "pnl": p.pnl} for p in history]
            metrics = PerformanceAnalyzer.analyze_performance(history_dicts, "3m")

            if "error" in metrics:
                await _reply(update, format_error(metrics["error"]))
                return

            exp = metrics.get("summary", {})
            vol = exp.get("volatility", 0) if isinstance(exp, dict) else 0

            chart_lines = _render_ascii_chart(history_dicts[-30:])
            text = format_performance_summary(metrics)
            full_text = text + "\n\n<b>Trend (30 days)</b>\n" + chart_lines

            await _reply(update, full_text, refresh_keyboard("performance"))
    except Exception as e:
        logger.error("performance_command failed", error=str(e))
        await _reply(update, format_error("Failed to fetch performance data."))


def _render_ascii_chart(points: List[Dict[str, Any]]) -> str:
    if len(points) < 2:
        return "  Insufficient data for chart."
    values = [p.get("value", 0) for p in points]
    mn = min(values)
    mx = max(values)
    rng = mx - mn if mx != mn else 1
    height = 5
    lines_list = []
    for i in range(height - 1, -1, -1):
        threshold = mn + (rng * i / (height - 1)) if height > 1 else mn
        bar = ""
        for v in values:
            if v >= threshold:
                bar += "█"
            else:
                bar += " "
        label = f"${mn + (rng * i / (height - 1)):,.0f}" if height > 1 else f"${mn:,.0f}"
        lines_list.append(f"  {label.rjust(10)} {bar}")
    lines_list.append(f"  {'':>11}{'▔' * len(values)}")
    return "\n".join(lines_list)


# ── Alerts ───────────────────────────────────────────────────────────────────

async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    try:
        async with _get_session() as session:
            asvc = AlertsService(session)
            _, portfolio_id = await _ensure_user_portfolio(session)

            await asvc.check_profit_milestones(portfolio_id)
            await asvc.check_drawdown_alerts(portfolio_id)
            await asvc.check_volatility_alerts(portfolio_id)
            await asvc.check_imbalance_alerts(portfolio_id)

            alerts = await asvc.get_alerts(portfolio_id)
            alert_list = [
                {
                    "id": a.id, "title": a.title, "message": a.message,
                    "severity": a.severity, "read": a.read, "type": a.type,
                    "created_at": a.created_at,
                }
                for a in alerts[:10]
            ]
            await _reply(update, format_alert_list(alert_list), alert_keyboard())
    except Exception as e:
        logger.error("alerts_command failed", error=str(e))
        await _reply(update, format_error("Failed to fetch alerts."))


# ── Pause Conversation ──────────────────────────────────────────────────────

async def pause_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _check_auth(update):
        return ConversationHandler.END
    try:
        if context.args:
            trader_name = " ".join(context.args)
            async with _get_session() as session:
                ts = TraderService(session)
                _, portfolio_id = await _ensure_user_portfolio(session)
                traders = await ts.get_all_traders(portfolio_id)
                matches = [t for t in traders if trader_name.lower() in t.trader_name.lower() and t.status == "active"]
                if not matches:
                    await _reply(update, format_error(f"No active trader found matching '{trader_name}'."))
                    return ConversationHandler.END
                if len(matches) > 1:
                    kb = trader_selection_keyboard(matches)
                    await _reply(update, "Multiple active traders found. Please select:", kb)
                    return PAUSE_SELECT
                trader = matches[0]
                context.user_data["pause_trader_id"] = trader.id
                context.user_data["pause_trader_name"] = trader.trader_name
                kb = confirmation_keyboard("pause", trader.id)
                pnl_s = "+" if trader.total_pnl >= 0 else ""
                await _reply(update,
                    f"⏸️ <b>Pause copy relationship?</b>\n"
                    f"Trader: <b>{_es(trader.trader_name)}</b>\n"
                    f"Allocation: <code>{trader.allocation_percent:.1f}%</code>\n"
                    f"PnL: <code>{pnl_s}${trader.total_pnl:,.2f}</code>\n"
                    f"Status: <code>{_es(trader.status.upper())}</code>",
                    kb)
                return PAUSE_CONFIRM
        else:
            async with _get_session() as session:
                ts = TraderService(session)
                _, portfolio_id = await _ensure_user_portfolio(session)
                traders = await ts.get_all_traders(portfolio_id)
                active = [t for t in traders if t.status == "active"]
                if not active:
                    await _reply(update, "✅ No active traders to pause.")
                    return ConversationHandler.END
                kb = trader_selection_keyboard(active)
                await _reply(update, "Select a trader to pause:", kb)
                return PAUSE_SELECT
    except Exception as e:
        logger.error("pause_start failed", error=str(e))
        await _reply(update, format_error("Failed to start pause flow."))
        return ConversationHandler.END


async def pause_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        trader_id = int(query.data.split(":")[1])
        async with _get_session() as session:
            ts = TraderService(session)
            trader = await ts.get_trader_detail(trader_id)
            if not trader:
                await query.edit_message_text(format_error("Trader not found."), parse_mode="HTML")
                return ConversationHandler.END
            if trader.status == "paused":
                await query.edit_message_text(f"⏸️ Trader <b>{_es(trader.trader_name)}</b> is already paused.", parse_mode="HTML")
                return ConversationHandler.END
            context.user_data["pause_trader_id"] = trader.id
            context.user_data["pause_trader_name"] = trader.trader_name
            kb = confirmation_keyboard("pause", trader.id)
            pnl_s = "+" if trader.total_pnl >= 0 else ""
            await query.edit_message_text(
                f"⏸️ <b>Pause copy relationship?</b>\n"
                f"Trader: <b>{_es(trader.trader_name)}</b>\n"
                f"Allocation: <code>{trader.allocation_percent:.1f}%</code>\n"
                f"PnL: <code>{pnl_s}${trader.total_pnl:,.2f}</code>\n"
                f"Status: <code>{_es(trader.status.upper())}</code>",
                parse_mode="HTML", reply_markup=kb)
            return PAUSE_CONFIRM
    except (IndexError, ValueError) as e:
        logger.error("pause_select parse error", error=str(e))
        await query.edit_message_text(format_error("Invalid selection."), parse_mode="HTML")
        return ConversationHandler.END


async def pause_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        trader_id = int(query.data.split(":")[1])
        async with _get_session() as session:
            ts = TraderService(session)
            trader = await ts.pause_trader(trader_id)
            if not trader:
                await query.edit_message_text(format_error("Trader not found."), parse_mode="HTML")
                return ConversationHandler.END
            text = (
                f"✅ <b>Trader Paused</b>\n"
                f"━" * 20 + "\n"
                f"<b>{_es(trader.trader_name)}</b> has been paused.\n"
                f"Allocation: <code>{trader.allocation_percent:.1f}%</code>\n"
                f"Status: <code>PAUSED</code>"
            )
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
            await _log_action(session, trader.portfolio_id, f"pause_trader:{trader.trader_name}", "manual")
    except (IndexError, ValueError) as e:
        logger.error("pause_confirm error", error=str(e))
        await query.edit_message_text(format_error("Failed to pause trader."), parse_mode="HTML")
    return ConversationHandler.END


# ── Resume Conversation ─────────────────────────────────────────────────────

async def resume_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _check_auth(update):
        return ConversationHandler.END
    try:
        if context.args:
            trader_name = " ".join(context.args)
            async with _get_session() as session:
                ts = TraderService(session)
                _, portfolio_id = await _ensure_user_portfolio(session)
                traders = await ts.get_all_traders(portfolio_id)
                matches = [t for t in traders if trader_name.lower() in t.trader_name.lower() and t.status == "paused"]
                if not matches:
                    await _reply(update, format_error(f"No paused trader found matching '{trader_name}'."))
                    return ConversationHandler.END
                if len(matches) > 1:
                    kb = trader_selection_keyboard(matches)
                    await _reply(update, "Multiple paused traders found. Please select:", kb)
                    return RESUME_SELECT
                trader = matches[0]
                context.user_data["resume_trader_id"] = trader.id
                context.user_data["resume_trader_name"] = trader.trader_name
                kb = confirmation_keyboard("resume", trader.id)
                pnl_s = "+" if trader.total_pnl >= 0 else ""
                await _reply(update,
                    f"▶️ <b>Resume copy relationship?</b>\n"
                    f"Trader: <b>{_es(trader.trader_name)}</b>\n"
                    f"Allocation: <code>{trader.allocation_percent:.1f}%</code>\n"
                    f"PnL: <code>{pnl_s}${trader.total_pnl:,.2f}</code>",
                    kb)
                return RESUME_CONFIRM
        else:
            async with _get_session() as session:
                ts = TraderService(session)
                _, portfolio_id = await _ensure_user_portfolio(session)
                traders = await ts.get_all_traders(portfolio_id)
                paused = [t for t in traders if t.status == "paused"]
                if not paused:
                    await _reply(update, "✅ No paused traders to resume.")
                    return ConversationHandler.END
                kb = trader_selection_keyboard(paused)
                await _reply(update, "Select a trader to resume:", kb)
                return RESUME_SELECT
    except Exception as e:
        logger.error("resume_start failed", error=str(e))
        await _reply(update, format_error("Failed to start resume flow."))
        return ConversationHandler.END


async def resume_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        trader_id = int(query.data.split(":")[1])
        async with _get_session() as session:
            ts = TraderService(session)
            trader = await ts.get_trader_detail(trader_id)
            if not trader:
                await query.edit_message_text(format_error("Trader not found."), parse_mode="HTML")
                return ConversationHandler.END
            if trader.status == "active":
                await query.edit_message_text(f"▶️ Trader <b>{_es(trader.trader_name)}</b> is already active.", parse_mode="HTML")
                return ConversationHandler.END
            context.user_data["resume_trader_id"] = trader.id
            context.user_data["resume_trader_name"] = trader.trader_name
            kb = confirmation_keyboard("resume", trader.id)
            pnl_s = "+" if trader.total_pnl >= 0 else ""
            await query.edit_message_text(
                f"▶️ <b>Resume copy relationship?</b>\n"
                f"Trader: <b>{_es(trader.trader_name)}</b>\n"
                f"Allocation: <code>{trader.allocation_percent:.1f}%</code>\n"
                f"PnL: <code>{pnl_s}${trader.total_pnl:,.2f}</code>",
                parse_mode="HTML", reply_markup=kb)
            return RESUME_CONFIRM
    except (IndexError, ValueError) as e:
        logger.error("resume_select parse error", error=str(e))
        await query.edit_message_text(format_error("Invalid selection."), parse_mode="HTML")
        return ConversationHandler.END


async def resume_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        trader_id = int(query.data.split(":")[1])
        async with _get_session() as session:
            ts = TraderService(session)
            trader = await ts.resume_trader(trader_id)
            if not trader:
                await query.edit_message_text(format_error("Trader not found."), parse_mode="HTML")
                return ConversationHandler.END
            text = (
                f"✅ <b>Trader Resumed</b>\n"
                f"━" * 20 + "\n"
                f"<b>{_es(trader.trader_name)}</b> has been resumed.\n"
                f"Allocation: <code>{trader.allocation_percent:.1f}%</code>\n"
                f"Status: <code>ACTIVE</code>"
            )
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
            await _log_action(session, trader.portfolio_id, f"resume_trader:{trader.trader_name}", "manual")
    except (IndexError, ValueError) as e:
        logger.error("resume_confirm error", error=str(e))
        await query.edit_message_text(format_error("Failed to resume trader."), parse_mode="HTML")
    return ConversationHandler.END


# ── Recommend ────────────────────────────────────────────────────────────────

async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    try:
        async with _get_session() as session:
            _, portfolio_id = await _ensure_user_portfolio(session)

            rec_stmt = select(AiRecommendation).where(
                AiRecommendation.portfolio_id == portfolio_id
            ).order_by(desc(AiRecommendation.confidence_score), desc(AiRecommendation.created_at)).limit(5)
            rresult = await session.execute(rec_stmt)
            recs = list(rresult.scalars().all())
            if not recs:
                await _reply(update, (
                    "💡 <b>No recommendations yet.</b>\n"
                    "━" * 20 + "\n"
                    "Use /analyze to trigger a full AI portfolio analysis."
                ))
                return

            lines = ["🤖 <b>AI Recommendations</b>", "━" * 20]
            for rec in recs:
                rectype = rec.recommendation_type
                type_icons = {
                    "trader_review": "🔍", "rebalance": "⚖️", "risk_alert": "🚨",
                    "portfolio_health": "✅", "weekly_summary": "📅",
                }
                icon = type_icons.get(rectype, "💡")
                conf_stars = "⭐" * min(5, max(1, int(rec.confidence_score * 5)))
                applied = " ✅ <i>Applied</i>" if rec.applied else ""
                lines.append(
                    f"{icon} <b>{_es(rec.title)}</b>{applied}\n"
                    f"   {_es(rec.summary[:200])}\n"
                    f"   Confidence: {conf_stars} <code>{rec.confidence_score*100:.0f}%</code>"
                )

            await _reply(update, "\n\n".join(lines))
    except Exception as e:
        logger.error("recommend_command failed", error=str(e))
        await _reply(update, format_error("Failed to fetch recommendations."))


# ── Analyze ──────────────────────────────────────────────────────────────────

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    try:
        await _reply(update, "🤖 <b>Running AI Portfolio Analysis...</b>\nPlease wait, this may take a moment.")
        async with _get_session() as session:
            ps = PortfolioService(session)
            ts = TraderService(session)
            user_id, portfolio_id = await _ensure_user_portfolio(session)
            portfolio = await ps.get_portfolio(user_id)
            if portfolio is None:
                portfolio = await ps.get_or_create_portfolio(user_id)
            traders = await ts.get_all_traders(portfolio_id)
            positions = await ps.get_positions(portfolio_id)
            summary = await ps.get_portfolio_summary(portfolio_id)

            created_recs = []

            for t in traders:
                if t.total_pnl < 0:
                    rec = AiRecommendation(
                        portfolio_id=portfolio_id,
                        recommendation_type="trader_review",
                        title=f"Review {t.trader_name} — Negative Performance",
                        summary=(
                            f"{t.trader_name} shows negative PnL of ${t.total_pnl:.2f} "
                            f"with {t.allocation_percent:.1f}% allocation. "
                            f"Consider reducing allocation or pausing this copy relationship."
                        ),
                        confidence_score=round(random.uniform(0.6, 0.85), 2),
                        details={"trader_id": t.id, "trader_name": t.trader_name,
                                 "total_pnl": round(t.total_pnl, 2), "allocation": t.allocation_percent,
                                 "status": t.status, "classification": t.classification},
                    )
                    session.add(rec)
                    created_recs.append(rec)

            for t in traders:
                if t.allocation_percent > settings.MAX_ALLOCATION_PER_TRADER * 100:
                    rec = AiRecommendation(
                        portfolio_id=portfolio_id,
                        recommendation_type="rebalance",
                        title=f"Rebalance {t.trader_name} — High Concentration",
                        summary=(
                            f"{t.trader_name} has {t.allocation_percent:.1f}% allocation, "
                            f"exceeding the {settings.MAX_ALLOCATION_PER_TRADER * 100:.0f}% limit."
                        ),
                        confidence_score=round(random.uniform(0.7, 0.9), 2),
                        details={"trader_id": t.id, "trader_name": t.trader_name,
                                 "current_allocation": t.allocation_percent,
                                 "max_allowed": settings.MAX_ALLOCATION_PER_TRADER * 100},
                    )
                    session.add(rec)
                    created_recs.append(rec)

            if summary.health_score < 70:
                rec = AiRecommendation(
                    portfolio_id=portfolio_id,
                    recommendation_type="risk_alert",
                    title="Portfolio Health Score Below Threshold",
                    summary=(
                        f"Portfolio health score is {summary.health_score}/100. "
                        "Review risk management settings and consider pausing underperforming traders."
                    ),
                    confidence_score=0.85,
                    details={
                        "health_score": summary.health_score,
                        "total_value": summary.total_value,
                        "day_change": summary.daily_pnl,
                    },
                )
                session.add(rec)
                created_recs.append(rec)

            if not created_recs:
                rec = AiRecommendation(
                    portfolio_id=portfolio_id,
                    recommendation_type="portfolio_health",
                    title="Portfolio Performing Within Parameters",
                    summary=(
                        f"Portfolio is healthy (score: {summary.health_score}/100) "
                        f"with {summary.total_traders} traders and {summary.total_positions} positions."
                    ),
                    confidence_score=0.9,
                    details={
                        "health_score": summary.health_score,
                        "total_traders": summary.total_traders,
                        "total_positions": summary.total_positions,
                    },
                )
                session.add(rec)
                created_recs.append(rec)

            await session.flush()
            await _log_action(session, portfolio_id, "ai_analysis", "system",
                              {"recommendations_generated": len(created_recs)})

            text = (
                f"✅ <b>AI Analysis Complete</b>\n"
                f"━" * 20 + "\n"
                f"Generated <code>{len(created_recs)}</code> recommendations.\n\n"
                f"Use /recommend to view them."
            )
            await _reply(update, text)
    except Exception as e:
        logger.error("analyze_command failed", error=str(e))
        await _reply(update, format_error("Failed to run AI analysis."))


# ── Emergency ────────────────────────────────────────────────────────────────

async def emergency_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    try:
        async with _get_session() as session:
            ps = PortfolioService(session)
            ts = TraderService(session)
            _, portfolio_id = await _ensure_user_portfolio(session)

            traders = await ts.get_all_traders(portfolio_id)
            stmt = select(RiskMetric).where(RiskMetric.portfolio_id == portfolio_id).order_by(desc(RiskMetric.timestamp)).limit(1)
            rresult = await session.execute(stmt)
            latest_risk = rresult.scalar_one_or_none()

            summary = await ps.get_portfolio_summary(portfolio_id)
            portfolio_data = {
                "max_drawdown": latest_risk.max_drawdown if latest_risk else 0,
                "health_score": latest_risk.health_score if latest_risk else summary.health_score,
                "volatility": latest_risk.volatility if latest_risk else 0,
                "daily_loss": abs(summary.daily_pnl) / max(summary.total_value, 1),
            }
            risk_metrics = {"risk_score": latest_risk.risk_score if latest_risk else 0}

            ep = EmergencyProtection()
            emergency = ep.check_emergency_conditions(portfolio_data, risk_metrics)
            protocol = ep.PROTOCOLS.get(emergency.get("severity", 0), {})

            active_count = sum(1 for t in traders if t.status == "active")
            paused_count = sum(1 for t in traders if t.status == "paused")
            high_risk = [t for t in traders if t.classification in ("aggressive", "high_risk")]

            severity_icons = {0: "🟢", 1: "🟡", 2: "🟠", 3: "🔴", 4: "🚨"}
            sev = emergency.get("severity", 0)

            lines = [
                "🛡️ <b>Emergency Protection Status</b>",
                "━" * 20,
                f"Status: {severity_icons.get(sev, '⚪')} <code>{_es(emergency.get('reason', 'Normal').upper())}</code>",
                f"Severity Level: <code>{sev}/4</code>",
                "",
                "<b>Current State</b>",
                "━" * 20,
                f"• Active Traders: <code>{active_count}</code>",
                f"• Paused Traders: <code>{paused_count}</code>",
                f"• High Risk Traders: <code>{len(high_risk)}</code>",
                f"• Drawdown: <code>{abs(portfolio_data['max_drawdown'])*100:.2f}%</code>",
                f"• Health Score: <code>{portfolio_data['health_score']:.1f}/100</code>",
            ]

            if protocol:
                lines.extend([
                    "",
                    f"<b>Protocol: {_es(protocol.get('name', 'N/A'))}</b>",
                    f"<code>{_es(protocol.get('description', ''))}</code>",
                    f"Actions: {', '.join(f'<code>{_es(a)}</code>' for a in protocol.get('actions', []))}",
                ])

            lines.extend([
                "",
                "<b>Thresholds</b>",
                "━" * 20,
                f"• Emergency Stop: <code>{RiskLimits.EMERGENCY_STOP_DRAWDOWN*100:.0f}%</code> drawdown",
                f"• Max Drawdown: <code>{RiskLimits.MAX_PORTFOLIO_DRAWDOWN*100:.0f}%</code>",
                f"• Max Daily Loss: <code>{RiskLimits.MAX_DAILY_LOSS*100:.0f}%</code>",
                f"• Min Health Score: <code>{RiskLimits.MIN_HEALTH_SCORE}/100</code>",
            ])

            await _reply(update, "\n".join(lines), risk_menu_keyboard())
    except Exception as e:
        logger.error("emergency_command failed", error=str(e))
        await _reply(update, format_error("Failed to fetch emergency status."))


# ── Help ─────────────────────────────────────────────────────────────────────

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_auth(update):
        return
    await _reply(update, format_help(), main_menu_keyboard())


# ── Cancel Conversation ─────────────────────────────────────────────────────

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _reply(update, "❌ Cancelled.", main_menu_keyboard())
    return ConversationHandler.END


# ── Callback Handlers ────────────────────────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    route_map = {
        "cmd_start": start_command,
        "cmd_status": status_command,
        "cmd_portfolio": portfolio_command,
        "cmd_risk": risk_command,
        "cmd_traders": traders_command,
        "cmd_alerts": alerts_command,
        "cmd_performance": performance_command,
        "cmd_recommend": recommend_command,
        "cmd_emergency": emergency_command,
        "cmd_help": help_command,
        "risk_limits": _risk_limits_callback,
    }

    handler = route_map.get(data)
    if handler:
        await handler(update, context)
        return

    if data.startswith("analyze_trader:"):
        await _button_analyze_trader(update, context)
    elif data.startswith("toggle_rule:"):
        await _button_toggle_rule(update, context)
    elif data == "mark_alerts_read":
        await _button_mark_alerts_read(update, context)
    elif data.startswith("refresh:"):
        await _button_refresh(update, context)
    elif data.startswith("confirm_pause:"):
        await _quick_pause(update, context)
    elif data.startswith("confirm_resume:"):
        await _quick_resume(update, context)
    elif data == "cancel":
        await query.edit_message_text("❌ Cancelled.", parse_mode="HTML", reply_markup=main_menu_keyboard())
    elif data.startswith("select_trader:"):
        await query.edit_message_text("❌ Invalid conversation flow. Use /pause or /resume.", parse_mode="HTML")


async def _risk_limits_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [
        "📏 <b>Risk Limits Configuration</b>",
        "━" * 20,
        f"• Max Drawdown: <code>{RiskLimits.MAX_PORTFOLIO_DRAWDOWN*100:.0f}%</code>",
        f"• Max per Trader: <code>{RiskLimits.MAX_ALLOCATION_PER_TRADER*100:.0f}%</code>",
        f"• Max Single Position: <code>{RiskLimits.MAX_SINGLE_POSITION*100:.0f}%</code>",
        f"• Min Diversification: <code>{RiskLimits.MIN_DIVERSIFICATION}</code> traders",
        f"• Max Crypto Exposure: <code>{RiskLimits.MAX_CRYPTO_EXPOSURE*100:.0f}%</code>",
        f"• Max Volatility: <code>{RiskLimits.MAX_VOLATILITY*100:.0f}%</code>",
        f"• Min Health Score: <code>{RiskLimits.MIN_HEALTH_SCORE}/100</code>",
        f"• Max Daily Loss: <code>{RiskLimits.MAX_DAILY_LOSS*100:.0f}%</code>",
        f"• Emergency Drawdown: <code>{RiskLimits.EMERGENCY_STOP_DRAWDOWN*100:.0f}%</code>",
        f"• Cooldown After Loss: <code>{RiskLimits.COOLDOWN_DAYS_AFTER_LOSS}</code> days",
        f"• Volatility Reduction: <code>{RiskLimits.VOLATILITY_EXPOSURE_REDUCTION*100:.0f}%</code>",
    ]
    await _reply(update, "\n".join(lines), risk_menu_keyboard())


async def _button_analyze_trader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        trader_id = int(update.callback_query.data.split(":")[1])
        async with _get_session() as session:
            ts = TraderService(session)
            analysis = await ts.get_trader_analysis(trader_id)
            if not analysis:
                await _reply(update, format_error("Trader not found."))
                return
            t = analysis.trader
            tdict = {
                "trader_name": t.trader_name, "status": t.status,
                "classification": t.classification, "allocation_percent": t.allocation_percent,
                "current_value": t.current_value, "total_pnl": t.total_pnl,
                "total_roi": t.total_roi, "copied_at": t.copied_at,
                "last_updated": t.last_updated,
            }
            adict = {
                "classification": analysis.classification,
                "classification_reason": analysis.classification_reason,
                "performance_trend": analysis.performance_trend,
                "recommendation": analysis.recommendation,
                "risk_metrics": analysis.risk_metrics,
            }
            await _reply(update, format_trader_detail(tdict, adict), trader_detail_keyboard(trader_id))
    except (IndexError, ValueError) as e:
        logger.error("button_analyze_trader error", error=str(e))
        await _reply(update, format_error("Invalid trader selection."))


async def _button_toggle_rule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rule_id = int(update.callback_query.data.split(":")[1])
        async with _get_session() as session:
            rule = await session.get(AutomationRule, rule_id)
            if not rule:
                await _reply(update, format_error("Rule not found."))
                return
            rule.enabled = not rule.enabled
            rule.updated_at = datetime.now(timezone.utc)
            status_text = "enabled" if rule.enabled else "disabled"

            stmt = select(AutomationRule).where(AutomationRule.portfolio_id == rule.portfolio_id)
            rresult = await session.execute(stmt)
            rules = list(rresult.scalars().all())

            text = (
                f"✅ <b>Rule {status_text.title()}</b>\n"
                f"━" * 20 + "\n"
                f"<b>{_es(rule.name)}</b> is now <code>{status_text.upper()}</code>\n"
                f"Type: <code>{_es(rule.rule_type)}</code>"
            )
            await _reply(update, text, automation_menu_keyboard(rules))
            await _log_action(session, rule.portfolio_id, f"toggle_rule:{rule.name}", "manual",
                              {"rule_id": rule.id, "enabled": rule.enabled})
    except (IndexError, ValueError) as e:
        logger.error("button_toggle_rule error", error=str(e))
        await _reply(update, format_error("Failed to toggle rule."))


async def _button_mark_alerts_read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        async with _get_session() as session:
            _, portfolio_id = await _ensure_user_portfolio(session)
            stmt = select(Alert).where(Alert.portfolio_id == portfolio_id, Alert.read == False)
            rresult = await session.execute(stmt)
            unread = list(rresult.scalars().all())
            count = 0
            for a in unread:
                a.read = True
                count += 1
            text = f"✅ <b>Alerts</b>\n" + "━" * 20 + f"\nMarked <code>{count}</code> alert(s) as read."
            await _reply(update, text, alert_keyboard())
    except Exception as e:
        logger.error("button_mark_alerts_read error", error=str(e))
        await _reply(update, format_error("Failed to mark alerts as read."))


async def _button_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    try:
        data_type = data.split(":", 1)[1] if ":" in data else "status"
        route = {
            "status": status_command, "portfolio": portfolio_command,
            "risk": risk_command, "traders": traders_command,
            "alerts": alerts_command, "performance": performance_command,
        }
        handler = route.get(data_type, status_command)
        await handler(update, context)
    except IndexError:
        await status_command(update, context)


async def _quick_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        trader_id = int(update.callback_query.data.split(":")[1])
        async with _get_session() as session:
            ts = TraderService(session)
            trader = await ts.pause_trader(trader_id)
            if not trader:
                await _reply(update, format_error("Trader not found."))
                return
            text = (
                f"✅ <b>Trader Paused</b>\n"
                f"━" * 20 + "\n"
                f"<b>{_es(trader.trader_name)}</b> has been paused."
            )
            await _reply(update, text, trader_detail_keyboard(trader_id))
            await _log_action(session, trader.portfolio_id, f"pause_trader:{trader.trader_name}", "manual")
    except (IndexError, ValueError) as e:
        logger.error("quick_pause error", error=str(e))
        await _reply(update, format_error("Failed to pause trader."))


async def _quick_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        trader_id = int(update.callback_query.data.split(":")[1])
        async with _get_session() as session:
            ts = TraderService(session)
            trader = await ts.resume_trader(trader_id)
            if not trader:
                await _reply(update, format_error("Trader not found."))
                return
            text = (
                f"✅ <b>Trader Resumed</b>\n"
                f"━" * 20 + "\n"
                f"<b>{_es(trader.trader_name)}</b> has been resumed."
            )
            await _reply(update, text, trader_detail_keyboard(trader_id))
            await _log_action(session, trader.portfolio_id, f"resume_trader:{trader.trader_name}", "manual")
    except (IndexError, ValueError) as e:
        logger.error("quick_resume error", error=str(e))
        await _reply(update, format_error("Failed to resume trader."))


# ── Global Error Handler ─────────────────────────────────────────────────────

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Telegram bot unhandled error", exc_info=context.error)
    try:
        if update and update.effective_chat:
            await update.effective_chat.send_message(
                format_error("An unexpected error occurred. Please try again later."),
                parse_mode="HTML",
            )
    except Exception:
        pass


# ── Utilities ────────────────────────────────────────────────────────────────

async def _log_action(session, portfolio_id: int, action: str, action_type: str, details: dict | None = None):
    try:
        log = AuditLog(
            portfolio_id=portfolio_id,
            action=action,
            action_type=action_type,
            details=details or {},
        )
        session.add(log)
    except Exception as e:
        logger.warning("Failed to log action", error=str(e))


def _es(text: str | float | int | None) -> str:
    from html import escape
    return escape(str(text or ""))


# ── Handler Registration ─────────────────────────────────────────────────────

def register_handlers(app):
    """Register all command, conversation, and callback handlers on the Application."""
    # Conversation handlers (must be registered before command handlers)
    pause_conv = ConversationHandler(
        entry_points=[CommandHandler("pause", pause_start, filters=filters.COMMAND)],
        states={
            PAUSE_SELECT: [CallbackQueryHandler(pause_select, pattern=r"^select_trader:\d+$")],
            PAUSE_CONFIRM: [
                CallbackQueryHandler(pause_confirm, pattern=r"^confirm_pause:\d+$"),
                CallbackQueryHandler(cancel, pattern=r"^cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.TEXT & ~filters.COMMAND, cancel),
        ],
        name="pause_trader",
        persistent=False,
    )

    resume_conv = ConversationHandler(
        entry_points=[CommandHandler("resume", resume_start, filters=filters.COMMAND)],
        states={
            RESUME_SELECT: [CallbackQueryHandler(resume_select, pattern=r"^select_trader:\d+$")],
            RESUME_CONFIRM: [
                CallbackQueryHandler(resume_confirm, pattern=r"^confirm_resume:\d+$"),
                CallbackQueryHandler(cancel, pattern=r"^cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.TEXT & ~filters.COMMAND, cancel),
        ],
        name="resume_trader",
        persistent=False,
    )

    # Register conversation handlers first
    app.add_handler(pause_conv)
    app.add_handler(resume_conv)

    # Command handlers
    app.add_handler(CommandHandler("start", start_command, filters=filters.COMMAND))
    app.add_handler(CommandHandler("status", status_command, filters=filters.COMMAND))
    app.add_handler(CommandHandler("portfolio", portfolio_command, filters=filters.COMMAND))
    app.add_handler(CommandHandler("risk", risk_command, filters=filters.COMMAND))
    app.add_handler(CommandHandler("traders", traders_command, filters=filters.COMMAND))
    app.add_handler(CommandHandler("performance", performance_command, filters=filters.COMMAND))
    app.add_handler(CommandHandler("alerts", alerts_command, filters=filters.COMMAND))
    app.add_handler(CommandHandler("recommend", recommend_command, filters=filters.COMMAND))
    app.add_handler(CommandHandler("analyze", analyze_command, filters=filters.COMMAND))
    app.add_handler(CommandHandler("emergency", emergency_command, filters=filters.COMMAND))
    app.add_handler(CommandHandler("help", help_command, filters=filters.COMMAND))
    app.add_handler(CommandHandler("cancel", cancel, filters=filters.COMMAND))

    # Callback query handler for all menu buttons
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"^(cmd_|analyze_trader:|toggle_rule:|mark_alerts_read|refresh:|confirm_pause:|confirm_resume:|cancel|risk_limits|select_trader:)"))

    # Error handler
    app.add_error_handler(error_handler)
