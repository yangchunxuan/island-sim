"""
世界编年史 — Island Sim v1

将重大事件汇成时间线，输出 world_reports/chronicle.md。
只记录里程碑事件（崩溃/恢复/首次/大规模的），避免日常噪音。
"""

import os
from typing import Any

CHRONICLE_DATA_PATH: str = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "world_reports", "chronicle.json",
)
CHRONICLE_READABLE_PATH: str = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "world_reports", "chronicle.md",
)


class WorldChronicle:
    """世界编年史。记录重大事件的时间线。"""

    # 只记录的事件类型
    MILESTONE_EVENTS: set[str] = {
        "REGION_COLLAPSE", "REGION_RECOVERY",
    }

    def __init__(self, data_path: str = CHRONICLE_DATA_PATH,
                 readable_path: str = CHRONICLE_READABLE_PATH) -> None:
        self._data_path = data_path
        self._readable_path = readable_path
        self._entries: list[dict[str, Any]] = []
        self._last_tick_recorded: dict[str, int] = {}
        self._dirty: bool = False
        self._save_counter: int = 0
        self._load()

    def update(self, tick: int, event_logger: object) -> None:
        """从事件记录中提取里程碑事件（仅新条目时标记dirty）"""
        events = event_logger.get_events_since(0)

        for event in events:
            et = event["event_type"]
            if et not in self.MILESTONE_EVENTS:
                continue
            if event.get("tick", 0) <= self._last_tick_recorded.get(et, -1):
                continue

            day = event["tick"] // 1200
            entry = self._format_entry(day, event)
            if entry:
                self._entries.append(entry)
                self._last_tick_recorded[et] = event["tick"]
                self._dirty = True

        # 有新增条目时才写盘（最多每1200tick一次）
        self._save_counter += 1
        if self._dirty and self._save_counter >= 600:
            self._save()
            self._dirty = False
            self._save_counter = 0

    def _format_entry(self, day: int, event: dict) -> dict | None:
        """将事件格式化为编年史条目"""
        et = event["event_type"]
        details = event.get("details", {})
        position = event.get("position", (0, 0))
        region_str = f"({position[0]},{position[1]})" if position else "?"

        if et == "REGION_COLLAPSE":
            return {
                "day": day, "tick": event.get("tick", 0),
                "text": f"区域{region_str}生态崩溃",
            }
        elif et == "REGION_RECOVERY":
            return {
                "day": day, "tick": event.get("tick", 0),
                "text": f"区域{region_str}生态恢复",
            }
        return None

    def _load(self) -> None:
        """从JSON数据文件加载"""
        if os.path.exists(self._data_path):
            import json
            try:
                with open(self._data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._entries = data.get("entries", [])
                if self._entries:
                    last_tick = max(e.get("tick", 0) for e in self._entries)
                    self._last_tick_recorded["REGION_COLLAPSE"] = last_tick
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

    def _save(self) -> None:
        """持久化编年史（JSON数据 + MD可读）"""
        import json
        data = {"entries": self._entries}
        os.makedirs(os.path.dirname(self._data_path), exist_ok=True)
        with open(self._data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._write_readable()

    def _write_readable(self) -> None:
        """写human-readable编年史MD文件"""
        if not self._entries:
            return
        lines = ["# 世界编年史", f"{'─'*40}", ""]
        prev_day = -1
        for entry in self._entries:
            d = entry["day"]
            if d != prev_day:
                lines.append(f"\n## Day {d}")
                prev_day = d
            lines.append(f"- {entry['text']}")

        with open(self._readable_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    @property
    def entries(self) -> list[dict]:
        return list(self._entries)


def tick_of_day(day: int) -> int:
    """天号转为tick数"""
    return day * 1200
