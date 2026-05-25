"""
事件记录器 — Island Sim v1

世界原始事件记录器。append-only，最大保留5000条，超限自动丢弃最旧事件。
"""

from typing import Any, Optional

MAX_EVENTS: int = 5000


class EventLogger:
    """世界原始事件记录器（append-only）"""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def log(
        self,
        tick: int,
        event_type: str,
        npc: Optional[str] = None,
        position: Optional[tuple[int, int]] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """记录一条新事件。超过MAX_EVENTS时自动丢弃最旧条目。"""
        event: dict[str, Any] = {
            "tick": tick,
            "event_type": event_type,
            "npc": npc,
            "position": position,
            "details": details or {},
        }
        self._events.append(event)
        self._trim()

    def _trim(self) -> None:
        if len(self._events) > MAX_EVENTS:
            self._events = self._events[-MAX_EVENTS:]

    def get_events(self) -> list[dict[str, Any]]:
        """返回所有事件副本"""
        return list(self._events)

    def get_events_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """按类型过滤事件"""
        return [e for e in self._events if e["event_type"] == event_type]

    def get_events_since(self, tick: int) -> list[dict[str, Any]]:
        """返回tick之后的所有事件"""
        return [e for e in self._events if e["tick"] >= tick]

    def clear(self) -> None:
        """清空所有事件"""
        self._events.clear()

    @property
    def count(self) -> int:
        return len(self._events)
