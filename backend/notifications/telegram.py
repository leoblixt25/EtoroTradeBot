import structlog
from typing import Any, Dict, Optional

logger = structlog.get_logger(__name__)


class NotificationService:
    def __init__(self, bot: Optional[Any] = None, chat_id: Optional[str] = None):
        self.bot = bot
        self.chat_id = chat_id

    def send_message(self, chat_id: Optional[str], text: str, parse_mode: str = "Markdown") -> bool:
        target = chat_id or self.chat_id
        if not target or not self.bot:
            logger.warning("telegram not configured, message not sent")
            return False
        try:
            self.bot.send_message(chat_id=target, text=text, parse_mode=parse_mode)
            return True
        except Exception as e:
            logger.error("failed to send telegram message", error=str(e))
            return False

    def send_portfolio_summary(self, chat_id: Optional[str], portfolio_data: Dict[str, Any]) -> bool:
        total = portfolio_data.get("total_value", 0)
        cash = portfolio_data.get("cash_balance", 0)
        invested = portfolio_data.get("invested_amount", 0)
        unrealized = portfolio_data.get("unrealized_pnl", 0)
        daily = portfolio_data.get("daily_pnl", 0)
        health = portfolio_data.get("health_score", 100)
        positions = portfolio_data.get("total_positions", 0)
        traders = portfolio_data.get("active_traders", 0)

        arrow = "\U0001f4c8" if unrealized >= 0 else "\U0001f4c9"
        health_icon = "\U0001f7e2" if health >= 70 else "\U0001f7e1" if health >= 40 else "\U0001f534"

        text = (
            f"\U0001f4ca *Portfolio Summary*\n\n"
            f"Total Value: `{self.format_currency(total)}`\n"
            f"Cash: `{self.format_currency(cash)}`\n"
            f"Invested: `{self.format_currency(invested)}`\n"
            f"Unrealized PnL: {arrow} `{self.format_currency(unrealized)}` ({self.format_percent(unrealized / invested if invested else 0)})\n"
            f"Daily PnL: `{self.format_currency(daily)}`\n\n"
            f"\U0001f4ca Positions: {positions} | Traders: {traders}\n"
            f"{health_icon} Health: {health:.0f}/100"
        )
        return self.send_message(chat_id, text)

    def send_risk_alert(self, chat_id: Optional[str], alert_data: Dict[str, Any]) -> bool:
        title = alert_data.get("alert_title", alert_data.get("title", "Risk Alert"))
        explanation = alert_data.get("explanation", alert_data.get("message", ""))
        urgency = alert_data.get("urgency", alert_data.get("severity", "medium"))
        actions = alert_data.get("recommended_actions", [])
        impact = alert_data.get("potential_impact", "")

        urgency_icons = {"immediate": "\U0001f534", "high": "\U0001f7e1", "medium": "\U0001f7e0", "low": "\U0001f535"}
        icon = urgency_icons.get(urgency.lower(), "\U000026a0")

        text = (
            f"{icon} *Risk Alert: {title}*\n\n"
            f"{explanation}\n"
        )
        if impact:
            text += f"\n*Impact:* {impact}\n"
        text += f"\n*Urgency:* {urgency.upper()}"
        if actions:
            text += f"\n\n*Recommended Actions:*"
            for a in actions:
                text += f"\n- {a}"
        return self.send_message(chat_id, text)

    def send_trader_alert(self, chat_id: Optional[str], trader_name: str, alert: Dict[str, Any]) -> bool:
        alert_type = alert.get("type", "update")
        details = alert.get("details", alert.get("message", ""))
        classification = alert.get("classification", "")
        recommendation = alert.get("recommendation", "")

        icons = {"underperformance": "\U000026a0", "risk_increase": "\U0001f534", "classification_change": "\U0001f504", "update": "\U0001f4ac"}
        icon = icons.get(alert_type, "\U0001f4ac")

        text = (
            f"{icon} *Trader Alert: {trader_name}*\n\n"
            f"{details}\n"
        )
        if classification:
            text += f"\n*Classification:* {classification.upper()}"
        if recommendation:
            text += f"\n*Recommendation:* {recommendation}"
        return self.send_message(chat_id, text)

    def send_profit_milestone(self, chat_id: Optional[str], data: Dict[str, Any]) -> bool:
        amount = data.get("amount", data.get("profit", 0))
        pct = data.get("percent", 0)
        source = data.get("source", "portfolio")
        message = data.get("message", f"Profit milestone reached!")

        text = (
            f"\U0001f389 *Profit Milestone!*\n\n"
            f"{message}\n"
            f"Amount: `{self.format_currency(amount)}`\n"
            f"Return: `{self.format_percent(pct)}`\n"
            f"Source: {source}"
        )
        return self.send_message(chat_id, text)

    def send_drawdown_warning(self, chat_id: Optional[str], data: Dict[str, Any]) -> bool:
        current = data.get("current_drawdown", data.get("drawdown", 0))
        limit = data.get("limit", 0.25)
        pct_val = current / limit * 100 if limit else 0

        severity = "\U0001f534" if pct_val > 90 else "\U0001f7e1" if pct_val > 70 else "\U0001f7e0"
        text = (
            f"{severity} *Drawdown Warning*\n\n"
            f"Current Drawdown: `{self.format_percent(current)}`\n"
            f"Limit: `{self.format_percent(limit)}`\n"
            f"Threshold Used: `{pct_val:.0f}%`\n"
        )
        if data.get("recommendation"):
            text += f"\n*Recommendation:* {data['recommendation']}"
        return self.send_message(chat_id, text)

    def send_weekly_summary(self, chat_id: Optional[str], summary_data: Dict[str, Any]) -> bool:
        review = summary_data.get("performance_review", "")
        events = summary_data.get("key_events", [])
        risk = summary_data.get("risk_assessment", "")
        recs = summary_data.get("recommendations", [])
        outlook = summary_data.get("outlook", "")

        text = (
            f"\U0001f4c5 *Weekly Portfolio Summary*\n\n"
            f"*Performance:*\n{review}\n\n"
        )
        if events:
            text += f"*Key Events:*\n"
            for e in events:
                text += f"- {e}\n"
            text += "\n"
        if risk:
            text += f"*Risk Assessment:*\n{risk}\n\n"
        if recs:
            text += f"*Recommendations:*\n"
            for r in recs:
                text += f"- {r}\n"
            text += "\n"
        if outlook:
            text += f"*Outlook:*\n{outlook}"
        return self.send_message(chat_id, text)

    def send_automation_action(self, chat_id: Optional[str], action_data: Dict[str, Any]) -> bool:
        action_type = action_data.get("action", action_data.get("type", "unknown"))
        status = action_data.get("status", "completed")
        details = action_data.get("details", {})

        status_icon = "\U00002705" if status == "completed" else "\U0000274c" if status == "failed" else "\U000026a0"

        text = (
            f"{status_icon} *Automation Action*\n\n"
            f"Action: `{action_type}`\n"
            f"Status: `{status}`\n"
        )
        if details:
            text += f"\n*Details:*\n`{str(details)[:300]}`"
        return self.send_message(chat_id, text)

    def send_error_notification(self, chat_id: Optional[str], error: str) -> bool:
        text = (
            f"\U0001f6a8 *System Error*\n\n"
            f"`{error[:500]}`\n\n"
            f"Please check logs for more details."
        )
        return self.send_message(chat_id, text)

    @staticmethod
    def format_number(value: float) -> str:
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}B"
        if value >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        if value >= 1_000:
            return f"{value:,.2f}"
        return f"{value:.2f}"

    @staticmethod
    def format_percent(value: float) -> str:
        if value > 1:
            return f"{value:.2f}%"
        return f"{abs(value) * 100:.2f}%"

    @staticmethod
    def format_currency(value: float, currency: str = "USD") -> str:
        symbols = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "BTC": "\u20bf"}
        sym = symbols.get(currency, "$")
        formatted = NotificationService.format_number(value)
        return f"{sym}{formatted}"
