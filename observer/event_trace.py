"""
事件追踪系统 — Island Sim v1

为每个原始事件分配唯一 event_id，支持反向查找。
所有 observer 叙事必须可追溯到原始 event。
"""

from typing import Any, Optional


class EventTrace:
    """事件追踪。分配唯一ID，支持 event_id → event 反向查找。"""

    def __init__(self) -> None:
        self._trace: dict[int, dict[str, Any]] = {}
        self._next_id: int = 0

    def register(self, event: dict[str, Any]) -> int:
        """注册一条事件，返回 event_id"""
        event_id = self._next_id
        self._next_id += 1
        self._trace[event_id] = {
            "event_id": event_id,
            "tick": event.get("tick", 0),
            "event_type": event.get("event_type", "UNKNOWN"),
            "npc": event.get("npc"),
            "position": event.get("position"),
            "details": dict(event.get("details", {})) if isinstance(event.get("details"), dict) else str(event.get("details", {})),
        }
        return event_id

    def lookup(self, event_id: int) -> Optional[dict[str, Any]]:
        """根据 event_id 查找原始事件"""
        return self._trace.get(event_id)

    def find_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """按类型查找事件"""
        return [
            {"id": eid, "event": ev}
            for eid, ev in self._trace.items()
            if ev["event_type"] == event_type
        ]

    def find_by_tick(self, tick: int) -> list[dict[str, Any]]:
        """按tick查找事件"""
        return [
            {"id": eid, "event": ev}
            for eid, ev in self._trace.items()
            if ev["tick"] == tick
        ]

    def get_last_event_id(self) -> int:
        """返回最后分配的 event_id"""
        return self._next_id - 1 if self._next_id > 0 else -1

    @property
    def count(self) -> int:
        return self._next_id
