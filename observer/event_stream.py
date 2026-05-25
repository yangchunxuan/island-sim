"""
事件流输出 — Island Sim v1

将实时事件写入 world_reports/event_stream.md，形成持续更新的日志流。
"""

import os
from datetime import datetime
from typing import Any

STREAM_PATH: str = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "world_reports", "event_stream.md",
)


class EventStream:
    """实时事件流输出器。每帧追加新事件到event_stream.md。"""

    def __init__(self, path: str = STREAM_PATH) -> None:
        self._path = path
        self._last_tick: int = -1
        self._written_count: int = 0

    def update(self, tick: int, event_logger: object) -> None:
        """追加tick以来的新事件到事件流文件"""
        new_events = event_logger.get_events_since(self._last_tick + 1)
        if not new_events:
            self._last_tick = tick
            return

        lines: list[str] = []
        for event in new_events:
            et = event["event_type"]
            npc = event.get("npc", "")
            pos = event.get("position", None)
            details = event.get("details", {})

            pos_str = f"({pos[0]},{pos[1]})" if pos else ""
            day = event["tick"] // 1200

            line = self._format_line(day, npc, et, pos_str, details)
            if line:
                lines.append(line)

        if lines:
            self._append_to_file(lines)

        self._last_tick = tick
        self._written_count += len(lines)

    def _format_line(
        self, day: int, npc: str, event_type: str,
        pos: str, details: dict,
    ) -> str:
        """单行事件格式化"""
        prefix = f"[Day {day}]"

        if event_type == "NPC_EAT":
            return f"{prefix} {npc} 进食（饥饿-{details.get('hunger_drop', '?')}）"
        elif event_type == "NPC_SLEEP":
            return f"{prefix} {npc} 入睡（体力{details.get('energy', '?')}）"
        elif event_type == "NPC_ENTER_WEAKENED":
            return f"{prefix} {npc} 进入虚弱状态"
        elif event_type == "NPC_RECOVER_WEAKENED":
            return f"{prefix} {npc} 从虚弱中恢复"
        elif event_type == "NPC_MOVE_REGION":
            return f"{prefix} {npc} 从{details.get('from','?')}移动到{details.get('to','?')}"
        elif event_type == "REGION_COLLAPSE":
            return f"{prefix} ⚠ 区域{pos}生态崩溃"
        elif event_type == "REGION_RECOVERY":
            return f"{prefix} 区域{pos}生态恢复"
        elif event_type == "RESOURCE_DEPLETED":
            return f"{prefix} 森林{pos}枯竭"
        elif event_type == "FOREST_RECOVERED":
            return f"{prefix} 森林{pos}恢复"
        elif event_type == "MUSHROOM_SPAWN":
            return f"{prefix} 蘑菇在{pos}生成"
        elif event_type == "FISH_SPAWN":
            return f"{prefix} 鱼在{pos}刷新"
        elif event_type == "NPC_BEHAVIOR_PROFILE":
            # 不要每次记录profile
            return ""
        return ""

    def _append_to_file(self, lines: list[str]) -> None:
        """追加行到事件流文件"""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        mode = "a" if os.path.exists(self._path) else "w"
        with open(self._path, mode, encoding="utf-8") as f:
            if mode == "w":
                f.write("# 世界事件流\n\n")
            for line in lines:
                f.write(line + "\n")

    @property
    def count(self) -> int:
        return self._written_count
