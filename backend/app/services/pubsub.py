import asyncio
from typing import Dict, Set

class PubSub:
    def __init__(self):
        # map of run_id to a set of queues
        self.subscribers: Dict[str, Set[asyncio.Queue]] = {}
        
    def subscribe(self, run_id: str) -> asyncio.Queue:
        if run_id not in self.subscribers:
            self.subscribers[run_id] = set()
        q = asyncio.Queue()
        self.subscribers[run_id].add(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue):
        if run_id in self.subscribers and q in self.subscribers[run_id]:
            self.subscribers[run_id].remove(q)
            if not self.subscribers[run_id]:
                del self.subscribers[run_id]

    async def publish(self, run_id: str, message: dict):
        if run_id in self.subscribers:
            for q in list(self.subscribers[run_id]):
                await q.put(message)

pubsub_broker = PubSub()
