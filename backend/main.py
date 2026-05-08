import structlog
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.config.settings import settings
from backend.config.logging_config import configure_logging
from backend.database.db import init_db
from backend.api.routes import router as api_router
from backend.api.websocket import manager
from backend.api.deps import scheduler_service
from telegram_bot.bot import BotRunner

logger = structlog.get_logger(__name__)
configure_logging()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting up", app_name=settings.APP_NAME)
    await init_db()

    from backend.database.db import async_session_factory
    from backend.services.settings_service import load_settings_into_memory
    async with async_session_factory() as session:
        await load_settings_into_memory(session)

    scheduler_service.start()

    if settings.TELEGRAM_BOT_TOKEN:
        try:
            bot = BotRunner()
            await bot.initialize()
            asyncio.create_task(bot.run_async())
            app.state.telegram_bot = bot
            logger.info("telegram bot started")
        except Exception as e:
            logger.error("telegram bot startup failed", error=str(e))
    else:
        logger.info("telegram bot not configured — skipping")

    portfolio_id = 1

    async def _do_sync(pid: int) -> None:
        try:
            from backend.database.db import async_session_factory
            from backend.services.portfolio_service import PortfolioService
            async with async_session_factory() as session:
                svc = PortfolioService(db=session)
                result = await svc.sync_portfolio(1)
                await session.commit()
                logger.info("auto sync completed", portfolio_id=pid, **result)
        except Exception as e:
            logger.error("auto sync failed", portfolio_id=pid, error=str(e))

    asyncio.create_task(_do_sync(portfolio_id))

    scheduler_service.schedule_periodic_sync(
        _do_sync,
        portfolio_id=portfolio_id,
        interval_minutes=15,
    )
    scheduler_service.schedule_periodic_analysis(
        portfolio_id,
        lambda pid: logger.info("periodic analysis", portfolio_id=pid),
        interval_minutes=60,
    )
    scheduler_service.schedule_risk_check(
        lambda pid: logger.info("risk check", portfolio_id=pid),
        portfolio_id=portfolio_id,
    )
    scheduler_service.schedule_daily_summary(
        lambda pid: logger.info("daily summary", portfolio_id=pid),
        portfolio_id=portfolio_id,
    )

    yield

    logger.info("shutting down")
    bot = getattr(app.state, "telegram_bot", None)
    if bot:
        await bot.stop()
    scheduler_service.stop()


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Assisted eToro Portfolio Management Platform. "
    "Capital preservation, risk management, and semi-automated optimization for copy-trading portfolios.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda r, e: JSONResponse(
    status_code=429,
    content={"detail": "Rate limit exceeded. Please slow down."},
))

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    structlog.get_logger("access").info(
        "request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )
    return response


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "The requested resource was not found"},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error("internal server error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"},
    )


app.include_router(api_router)


GIT_COMMIT = "6dbfcbd"


@app.get("/health", response_model=dict)
async def health_check():
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "version": "1.0.0",
        "commit": GIT_COMMIT,
        "paper_trading": settings.PAPER_TRADING,
        "automation_enabled": settings.ENABLE_AUTOMATION,
        "timestamp": time.time(),
    }


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, portfolio_id: int = 1):
    await manager.connect(portfolio_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(portfolio_id, {
                "type": "echo",
                "data": data,
                "timestamp": time.time(),
            })
    except WebSocketDisconnect:
        manager.disconnect(portfolio_id, websocket)
    except Exception as e:
        logger.error("websocket error", error=str(e))
        manager.disconnect(portfolio_id, websocket)
