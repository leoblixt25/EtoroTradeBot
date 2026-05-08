import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import AppSetting
from backend.config.settings import settings

logger = structlog.get_logger(__name__)

SETTING_KEYS = {
    "ETORO_PUBLIC_API_KEY": "etoro_public_api_key",
    "ETORO_USER_KEY": "etoro_user_key",
    "PAPER_TRADING": "paper_trading",
    "ETORO_DEMO_MODE": "etoro_demo_mode",
    "TELEGRAM_BOT_TOKEN": "telegram_bot_token",
    "TELEGRAM_CHAT_ID": "telegram_chat_id",
}

KEY_TO_ATTR = {v: k for k, v in SETTING_KEYS.items()}


async def load_settings_into_memory(db: AsyncSession) -> None:
    stmt = select(AppSetting)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    for row in rows:
        attr = KEY_TO_ATTR.get(row.key)
        if attr is None:
            continue
        if attr in ("PAPER_TRADING", "ETORO_DEMO_MODE"):
            setattr(settings, attr, row.value.lower() == "true")
        else:
            setattr(settings, attr, row.value)
    if rows:
        logger.info("loaded persisted settings into memory", count=len(rows))


async def save_setting(db: AsyncSession, key: str, value: str) -> None:
    db_key = SETTING_KEYS.get(key)
    if db_key is None:
        return
    stmt = select(AppSetting).where(AppSetting.key == db_key)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=db_key, value=value))
