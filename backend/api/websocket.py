import structlog
import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, portfolio_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        if portfolio_id not in self.active_connections:
            self.active_connections[portfolio_id] = set()
        self.active_connections[portfolio_id].add(websocket)
        logger.info(
            "websocket connected",
            portfolio_id=portfolio_id,
            total=len(self.active_connections[portfolio_id]),
        )

    def disconnect(self, portfolio_id: int, websocket: WebSocket) -> None:
        if portfolio_id in self.active_connections:
            self.active_connections[portfolio_id].discard(websocket)
            if not self.active_connections[portfolio_id]:
                del self.active_connections[portfolio_id]
        logger.info(
            "websocket disconnected",
            portfolio_id=portfolio_id,
        )

    async def _send_to_connection(self, websocket: WebSocket, message: dict) -> bool:
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning("websocket send failed", error=str(e))
            return False

    async def broadcast(self, portfolio_id: int, message: dict) -> int:
        sent_count = 0
        connections = self.active_connections.get(portfolio_id, set()).copy()
        for websocket in connections:
            success = await self._send_to_connection(websocket, message)
            if success:
                sent_count += 1
            else:
                self.disconnect(portfolio_id, websocket)
        return sent_count

    async def send_portfolio_update(
        self, portfolio_id: int, data: dict
    ) -> int:
        message = {
            "type": "portfolio_update",
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return await self.broadcast(portfolio_id, message)

    async def send_alert(self, portfolio_id: int, alert: dict) -> int:
        message = {
            "type": "alert",
            "data": alert,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return await self.broadcast(portfolio_id, message)

    async def send_risk_alert(self, portfolio_id: int, risk_data: dict) -> int:
        message = {
            "type": "risk_alert",
            "data": risk_data,
            "severity": risk_data.get("severity", "info"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return await self.broadcast(portfolio_id, message)


manager = ConnectionManager()


async def periodic_portfolio_push(portfolio_id: int, get_data_func, interval: int = 30):
    while True:
        try:
            data = await get_data_func()
            await manager.send_portfolio_update(portfolio_id, data)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("periodic push error", error=str(e))
        await asyncio.sleep(interval)
