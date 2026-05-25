"""
模式分析器 — Island Sim v1

分析事件记录，输出：高频区域、NPC行为倾向、资源趋势、世界压力。
"""

from typing import Any

from observer.event_logger import EventLogger


class PatternAnalyzer:
    """行为模式分析器。读取事件记录，输出结构化分析报告。"""

    def __init__(self, event_logger: EventLogger) -> None:
        self._logger = event_logger

    def analyze(
        self,
        tick: int,
        npcs: list,
        resource_mgr: object,
    ) -> dict[str, Any]:
        """生成当前tick的模式分析报告"""
        current_day = tick // 1200
        return {
            "day": current_day,
            "tick": tick,
            "hot_regions": self._analyze_hot_regions(tick),
            "npc_tendencies": self._analyze_npc_tendencies(tick, npcs),
            "resource_trends": self._analyze_resource_trends(tick, resource_mgr),
            "world_pressure": self._analyze_world_pressure(npcs),
        }

    def _analyze_hot_regions(self, tick: int) -> list[dict[str, Any]]:
        """检测高频/低频活动区域（基于最近3天的NPC_MOVE_REGION事件）"""
        lookback = max(0, tick - 3 * 1200)
        region_events = self._logger.get_events_since(lookback)
        region_moves = [e for e in region_events if e["event_type"] == "NPC_MOVE_REGION"]

        counts: dict[str, int] = {}
        for e in region_moves:
            region = e["details"].get("to", "未知")
            counts[region] = counts.get(region, 0) + 1

        if not counts:
            return []

        sorted_regions = sorted(counts.items(), key=lambda x: -x[1])
        total = sum(counts.values()) or 1
        return [
            {
                "name": r,
                "count": c,
                "ratio": c / total,
            }
            for r, c in sorted_regions
        ]

    def _analyze_npc_tendencies(
        self, tick: int, npcs: list,
    ) -> list[dict[str, Any]]:
        """分析每个NPC的行为倾向"""
        tendencies = []
        for npc in npcs:
            name = getattr(npc, "name", "Unknown")
            state = npc.get_state()
            weakened = bool(getattr(npc, "_weakened", False))
            hunger = int(getattr(npc, "hunger", 0))
            mood = int(getattr(npc, "mood", 0))

            # 通过事件记录判断海岸倾向
            lookback = max(0, tick - 5 * 1200)
            events = self._logger.get_events_since(lookback)
            npc_events = [e for e in events if e.get("npc") == name]

            coastal_count = sum(
                1 for e in npc_events
                if e["details"].get("to") in ("西南", "东南")
                and e["event_type"] == "NPC_MOVE_REGION"
            )
            total_moves = sum(
                1 for e in npc_events
                if e["event_type"] == "NPC_MOVE_REGION"
            )

            tendencies.append({
                "name": name,
                "state": state,
                "weakened": weakened,
                "hunger": hunger,
                "mood": mood,
                "coastal_tendency": total_moves > 0 and coastal_count / total_moves > 0.5,
                "recent_moves": total_moves,
            })
        return tendencies

    def _analyze_resource_trends(
        self, tick: int, resource_mgr: object,
    ) -> dict[str, Any]:
        """分析资源趋势"""
        total_food = resource_mgr.total_food_remaining()
        depleted = len(resource_mgr.depleted_forests)
        total_forests = getattr(resource_mgr, "forest_count", lambda: 1)()
        depletion_rate = depleted / total_forests if total_forests > 0 else 0.0

        # 最近24小时的资源事件
        lookback = max(0, tick - 1200)
        recent = self._logger.get_events_since(lookback)
        mushroom_spawns = len([e for e in recent if e["event_type"] == "MUSHROOM_SPAWN"])
        fish_spawns = len([e for e in recent if e["event_type"] == "FISH_SPAWN"])
        recoveries = len([e for e in recent if e["event_type"] == "FOREST_RECOVERED"])

        return {
            "total_food": total_food,
            "depleted_count": depleted,
            "depletion_rate": round(depletion_rate, 3),
            "recovery_active": recoveries > 0,
            "mushroom_activity": mushroom_spawns,
            "fish_activity": fish_spawns,
        }

    def _analyze_world_pressure(self, npcs: list) -> dict[str, Any]:
        """分析世界生存压力"""
        if not npcs:
            return {
                "avg_hunger": 0.0,
                "avg_energy": 0.0,
                "avg_mood": 0.0,
                "weakened_count": 0,
                "npc_count": 0,
            }

        total = len(npcs)
        weakened_count = sum(1 for n in npcs if bool(getattr(n, "_weakened", False)))
        avg_hunger = sum(int(getattr(n, "hunger", 0)) for n in npcs) / total
        avg_energy = sum(int(getattr(n, "energy", 0)) for n in npcs) / total
        avg_mood = sum(int(getattr(n, "mood", 0)) for n in npcs) / total

        return {
            "avg_hunger": round(avg_hunger, 1),
            "avg_energy": round(avg_energy, 1),
            "avg_mood": round(avg_mood, 1),
            "weakened_count": weakened_count,
            "npc_count": total,
        }
