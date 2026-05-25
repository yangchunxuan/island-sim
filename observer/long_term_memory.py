"""
长期记忆统计 — Island Sim v1

持久化跟踪世界历史数据：最高饥饿、最危险区域、资源崩溃次数、
NPC生存天数、长期平均mood。每日写入world_memory.json。
"""

import json
import os
from typing import Any, Optional

MEMORY_PATH: str = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "world_memory.json"
)


class LongTermMemory:
    """长期记忆统计。记录世界持续运行的累积数据。"""

    def __init__(self, path: str = MEMORY_PATH) -> None:
        self._path = path
        self.all_time_max_hunger: float = 0.0
        self.all_time_max_hunger_npc: str = ""
        self.region_collapses: dict[tuple[int, int], int] = {}
        self.total_collapses: int = 0
        self.npc_survival_days: dict[str, int] = {}
        self.mood_samples: list[float] = []
        self.days_simulated: int = 0
        self.last_saved_day: int = -1
        self._load()

    def update(
        self,
        tick: int,
        npcs: list,
        pressure_map: Optional[object] = None,
    ) -> None:
        """从当前游戏状态更新统计数据"""
        current_day = tick // 1200

        # 更新天数
        self.days_simulated = max(self.days_simulated, current_day)

        # NPC数据
        for npc in npcs:
            name = getattr(npc, "name", "Unknown")
            hunger = getattr(npc, "hunger", 0)
            mood = getattr(npc, "mood", 50)

            # 历史最高饥饿
            if hunger > self.all_time_max_hunger:
                self.all_time_max_hunger = hunger
                self.all_time_max_hunger_npc = name

            # 生存天数（取最大）
            prev = self.npc_survival_days.get(name, 0)
            self.npc_survival_days[name] = max(prev, current_day)

            # mood采样
            self.mood_samples.append(float(mood))

        # 区域崩溃（从pressure_map）
        if pressure_map is not None:
            collapsed = getattr(pressure_map, "collapsed_regions", set())
            for region in collapsed:
                key = tuple(region) if not isinstance(region, tuple) else region
                self.region_collapses[key] = self.region_collapses.get(key, 0) + 1
                self.total_collapses += 1

        # 每日持久化
        if current_day > self.last_saved_day:
            self.save()
            self.last_saved_day = current_day

    def get_summary(self) -> dict[str, Any]:
        """返回历史摘要（用于叙事生成）"""
        avg_mood = (
            round(sum(self.mood_samples) / len(self.mood_samples), 1)
            if self.mood_samples
            else 50.0
        )
        most_dangerous = max(
            self.region_collapses, key=self.region_collapses.get
        ) if self.region_collapses else None

        return {
            "days_simulated": self.days_simulated,
            "all_time_max_hunger": round(self.all_time_max_hunger, 1),
            "all_time_max_hunger_npc": self.all_time_max_hunger_npc,
            "most_dangerous_region": (
                f"({most_dangerous[0]},{most_dangerous[1]})"
                if most_dangerous else "无记录"
            ),
            "most_dangerous_collapses": (
                self.region_collapses.get(most_dangerous, 0)
                if most_dangerous else 0
            ),
            "total_collapses": self.total_collapses,
            "avg_mood_long_term": avg_mood,
            "npc_days": dict(self.npc_survival_days),
        }

    def save(self) -> None:
        """持久化到world_memory.json"""
        data = {
            "all_time_max_hunger": self.all_time_max_hunger,
            "all_time_max_hunger_npc": self.all_time_max_hunger_npc,
            "region_collapses": {
                f"{r[0]},{r[1]}": c
                for r, c in self.region_collapses.items()
            },
            "total_collapses": self.total_collapses,
            "npc_survival_days": self.npc_survival_days,
            "mood_samples": self.mood_samples,
            "days_simulated": self.days_simulated,
        }
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self) -> None:
        """从world_memory.json恢复"""
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.all_time_max_hunger = data.get("all_time_max_hunger", 0.0)
            self.all_time_max_hunger_npc = data.get("all_time_max_hunger_npc", "")
            self.region_collapses = {
                tuple(int(c) for c in k.split(",")): v
                for k, v in data.get("region_collapses", {}).items()
            }
            self.total_collapses = data.get("total_collapses", 0)
            self.npc_survival_days = data.get("npc_survival_days", {})
            self.mood_samples = data.get("mood_samples", [])
            self.days_simulated = data.get("days_simulated", 0)
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
