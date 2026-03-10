import asyncio
import json
from typing import Callable, Awaitable

class EventBus:
    def __init__(self):
        self.subscribers: list[Callable[[dict], Awaitable[None]]] = []

    def subscribe(self, callback: Callable[[dict], Awaitable[None]]):
        if callback not in self.subscribers:
            self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[dict], Awaitable[None]]):
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    async def emit(self, event_type: str, analysis_id: str, data: dict):
        message = {
            "type": event_type,
            "analysis_id": analysis_id,
            "data": data
        }
        
        # Create tasks for all subscribers to avoid blocking
        tasks = []
        for sub in self.subscribers:
            tasks.append(asyncio.create_task(self._safe_call(sub, message)))
            
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    async def _safe_call(self, callback, message):
        try:
            await callback(message)
        except Exception as e:
            print(f"EventBus error calling subscriber: {e}")

event_bus = EventBus()
