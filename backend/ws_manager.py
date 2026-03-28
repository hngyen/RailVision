"""
WebSocket manager for RailVision.

Subscribes to the Redis rv:changes Pub/Sub channel and fans out
change events to connected WebSocket clients, filtered by stop_id.

Each client connects to /ws/{stop_id} and receives only events
relevant to that station.
"""

import asyncio
import json
import logging
from fastapi import WebSocket, WebSocketDisconnect

import redis_state

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks active WebSocket connections grouped by stop_id."""

    def __init__(self):
        # stop_id -> set of WebSocket connections
        self._subscriptions: dict[str, set[WebSocket]] = {}
        self._listener_task: asyncio.Task | None = None

    @property
    def active_count(self) -> int:
        return sum(len(conns) for conns in self._subscriptions.values())

    async def connect(self, websocket: WebSocket, stop_id: str):
        await websocket.accept()
        if stop_id not in self._subscriptions:
            self._subscriptions[stop_id] = set()
        self._subscriptions[stop_id].add(websocket)
        logger.info("WS client connected for stop_id=%s (total=%d)", stop_id, self.active_count)

        # Start the Redis listener on first connection
        if self._listener_task is None or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._redis_listener())

    def disconnect(self, websocket: WebSocket, stop_id: str):
        if stop_id in self._subscriptions:
            self._subscriptions[stop_id].discard(websocket)
            if not self._subscriptions[stop_id]:
                del self._subscriptions[stop_id]
        logger.info("WS client disconnected for stop_id=%s (total=%d)", stop_id, self.active_count)

    async def _redis_listener(self):
        """Subscribe to rv:changes and fan out to WebSocket clients."""
        r = await redis_state.get_redis()
        if r is None:
            logger.warning("Redis unavailable — WebSocket push disabled")
            return

        pubsub = r.pubsub()
        await pubsub.subscribe(redis_state.CHANNEL)
        logger.info("Redis Pub/Sub listener started on channel=%s", redis_state.CHANNEL)

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                try:
                    event = json.loads(message["data"])
                except (json.JSONDecodeError, TypeError):
                    continue

                stop_id = event.get("stop_id")
                if not stop_id or stop_id not in self._subscriptions:
                    continue

                # Fan out to all clients watching this stop
                dead = []
                for ws in self._subscriptions[stop_id]:
                    try:
                        await ws.send_json(event)
                    except Exception:
                        dead.append(ws)

                for ws in dead:
                    self._subscriptions[stop_id].discard(ws)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Redis listener error: %s", e)
        finally:
            await pubsub.unsubscribe(redis_state.CHANNEL)
            await pubsub.aclose()


manager = ConnectionManager()
