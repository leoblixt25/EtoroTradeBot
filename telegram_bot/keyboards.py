from typing import List, Any, Dict
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def _btn(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, callback_data=callback_data)


def _row(*buttons: InlineKeyboardButton) -> List[InlineKeyboardButton]:
    return list(buttons)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            _row(_btn("📊 Portfolio", "cmd_status"), _btn("📋 Positions", "cmd_portfolio")),
            _row(_btn("⚠️ Risk", "cmd_risk"), _btn("👤 Traders", "cmd_traders")),
            _row(_btn("🔔 Alerts", "cmd_alerts"), _btn("📈 Performance", "cmd_performance")),
            _row(_btn("🤖 AI Recommend", "cmd_recommend"), _btn("🛡️ Emergency", "cmd_emergency")),
            _row(_btn("❓ Help", "cmd_help")),
        ]
    )


def trader_detail_keyboard(trader_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            _row(_btn("🔍 Analyze", f"analyze_trader:{trader_id}")),
            _row(_btn("⏸️ Pause", f"confirm_pause:{trader_id}"), _btn("▶️ Resume", f"confirm_resume:{trader_id}")),
            _row(_btn("⬅️ Back to Traders", "cmd_traders")),
        ]
    )


def alert_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            _row(_btn("✅ Mark All Read", "mark_alerts_read"), _btn("🔄 Refresh", "cmd_alerts")),
            _row(_btn("⬅️ Main Menu", "cmd_start")),
        ]
    )


def confirmation_keyboard(action: str, item_id: int | str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            _row(
                _btn("✅ Confirm", f"confirm_{action}:{item_id}"),
                _btn("❌ Cancel", "cancel"),
            ),
        ]
    )


def risk_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            _row(_btn("📊 Risk Summary", "cmd_risk"), _btn("📏 Limits", "risk_limits")),
            _row(_btn("🛡️ Emergency", "cmd_emergency")),
            _row(_btn("⬅️ Main Menu", "cmd_start")),
        ]
    )


def automation_menu_keyboard(rules: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    buttons = []
    for rule in rules:
        name = rule.get("name", "Unknown Rule")
        enabled = rule.get("enabled", False)
        rule_id = rule.get("id", 0)
        toggle_label = f"✅ {name}" if enabled else f"⬜ {name}"
        buttons.append(_row(_btn(toggle_label, f"toggle_rule:{rule_id}")))
    buttons.append(_row(_btn("⬅️ Back", "cmd_start")))
    return InlineKeyboardMarkup(buttons)


def trader_selection_keyboard(traders: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    buttons = []
    for t in traders:
        name = t.get("trader_name", "Unknown")
        tid = t.get("id", 0)
        status = t.get("status", "unknown")
        icon = "🟢" if status == "active" else "⏸️"
        buttons.append(_row(_btn(f"{icon} {name}", f"select_trader:{tid}")))
    buttons.append(_row(_btn("❌ Cancel", "cancel")))
    return InlineKeyboardMarkup(buttons)


def refresh_keyboard(data_type: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            _row(_btn("🔄 Refresh", f"refresh:{data_type}")),
            _row(_btn("⬅️ Main Menu", "cmd_start")),
        ]
    )
