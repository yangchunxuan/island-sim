"""
实时事件流 — Island Sim v1

Append-only 实时事件环形缓冲区。
保留最近 N 条事件，自动裁剪。
支持事件等级：INFO / WARNING / CRITICAL / ECOLOGY / MOVEMENT。
支持 event_id / confidence / region / evidence_preview 元数据。
"""

from typing import Any


class LiveFeed:
    """实时事件流。append-only，自动裁剪。"""

    def __init__(self, max_entries: int = 200) -> None:
        self._max = max_entries
        self._entries: list[dict[str, Any]] = []

    def append(
        self,
        tick: int,
        level: str,
        message: str,
        event_id: int = -1,
        confidence: float = 1.0,
        region: str = "",
        evidence_preview: str = "",
    ) -> None:
        """追加一条事件，超限自动裁剪"""
        self._entries.append({
            "tick": tick,
            "level": level,
            "message": message,
            "event_id": event_id,
            "confidence": confidence,
            "region": region,
            "evidence_preview": evidence_preview,
        })
        if len(self._entries) > self._max:
            trim_count = len(self._entries) - self._max
            self._entries = self._entries[trim_count:]

    def recent(self, count: int = 10) -> list[dict[str, Any]]:
        """返回最近 N 条"""
        return self._entries[-count:]

    def all(self) -> list[dict[str, Any]]:
        """返回全部事件"""
        return list(self._entries)

    def clear(self) -> None:
        """清空"""
        self._entries.clear()

    def format_display_line(self, entry: dict[str, Any]) -> str:
        """格式化单条显示行: [event_id][confidence] level message (region)"""
        eid = entry.get("event_id", -1)
        conf = entry.get("confidence", 1.0)
        level = entry.get("level", "INFO")
        msg = entry.get("message", "")
        region = entry.get("region", "")
        evidence = entry.get("evidence_preview", "")
        line = f"[{eid}][{conf:.2f}] [{level}] {msg}"
        if region:
            line += f" ({region})"
        if evidence:
            line += f" — {evidence}"
        return line

    def get_display_entries(self, count: int = 10) -> list[str]:
        """返回最近 N 条的格式化显示行（最新在底部）"""
        return [
            self.format_display_line(e) for e in self.recent(count)
        ]

    @property
    def count(self) -> int:
        return len(self._entries)
