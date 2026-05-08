from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from backend.database.db import get_db
from backend.database.models import User
from backend.services.portfolio_service import PortfolioService
from backend.services.trader_service import TraderService
from backend.services.alerts_service import AlertsService
from backend.services.scheduler import SchedulerService
from backend.config.settings import settings
import structlog

logger = structlog.get_logger(__name__)


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token == settings.SECRET_KEY:
            from sqlalchemy import select
            stmt = select(User).limit(1)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                return user

    from sqlalchemy import select
    stmt = select(User).limit(1)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            username="default",
            email="default@etoro.local",
            hashed_password="placeholder",
        )
        db.add(user)
        await db.flush()
        logger.info("created default user")
    return user


async def get_portfolio_service(
    db: AsyncSession = Depends(get_db),
) -> PortfolioService:
    return PortfolioService(db=db)


async def get_trader_service(
    db: AsyncSession = Depends(get_db),
) -> TraderService:
    return TraderService(db=db)


async def get_alerts_service(
    db: AsyncSession = Depends(get_db),
) -> AlertsService:
    return AlertsService(db=db)


async def get_automation_engine(
    db: AsyncSession = Depends(get_db),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
) -> dict:
    return {
        "db": db,
        "portfolio_service": portfolio_service,
        "settings": settings,
    }


async def get_analytics_service(
    db: AsyncSession = Depends(get_db),
) -> dict:
    return {"db": db}


async def get_claude_client() -> dict:
    return {
        "api_key": settings.CLAUDE_API_KEY,
        "model": settings.CLAUDE_MODEL,
        "enabled": settings.CLAUDE_API_KEY is not None,
    }


async def get_telegram_bot() -> dict:
    return {
        "token": settings.TELEGRAM_BOT_TOKEN,
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "enabled": settings.TELEGRAM_BOT_TOKEN is not None and settings.TELEGRAM_CHAT_ID is not None,
    }


scheduler_service = SchedulerService()
