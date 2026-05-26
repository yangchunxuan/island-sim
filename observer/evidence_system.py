"""
证据链系统 — Island Sim v1

事件发生时收集上下文快照作为证据。
每条 observer 叙事必须附带 evidence。
禁止无证据来源的日志输出。
"""

from typing import Any, Optional


class EvidenceSystem:
    """证据链。记录事件发生时的world state快照。"""

    def __init__(self) -> None:
        self._evidence_store: dict[int, dict[str, Any]] = {}

    def collect_npc_evidence(
        self,
        npc: object,
        resource_mgr: object,
        pressure_map: object = None,
    ) -> dict[str, Any]:
        """收集NPC相关的world state快照"""
        evidence: dict[str, Any] = {
            "hunger": getattr(npc, "hunger", 0),
            "energy": getattr(npc, "energy", 0),
            "position": (getattr(npc, "x", 0), getattr(npc, "y", 0)),
            "weakened": getattr(npc, "_weakened", False),
            "state": getattr(npc, "get_state", lambda: "?")(),
            "nearby_food": self._count_nearby_food(npc, resource_mgr),
        }
        # 区域压力
        if pressure_map is not None and hasattr(npc, "x") and hasattr(npc, "y"):
            region = pressure_map.tile_to_region(
                getattr(npc, "x", 0), getattr(npc, "y", 0),
            )
            if region:
                evidence["region_pressure"] = round(
                    pressure_map.get_score(region[0], region[1]), 2,
                )
        return evidence

    def collect_resource_evidence(
        self,
        x: int, y: int,
        resource_mgr: object,
    ) -> dict[str, Any]:
        """收集资源事件证据"""
        evidence: dict[str, Any] = {
            "total_food": resource_mgr.total_food_remaining()
            if hasattr(resource_mgr, "total_food_remaining") else 0,
            "depleted_forests": len(
                getattr(resource_mgr, "depleted_forests", set())
            ),
            "mushroom_count": len(
                getattr(resource_mgr, "mushrooms", {})
            ),
            "fish_count": len(
                getattr(resource_mgr, "fish", {})
            ),
        }
        return evidence

    def store(self, event_id: int, evidence: dict[str, Any]) -> None:
        """存储事件证据"""
        self._evidence_store[event_id] = dict(evidence)

    def get_evidence(self, event_id: int) -> dict[str, Any]:
        """获取事件的证据"""
        return self._evidence_store.get(event_id, {})

    def compute_confidence(self, event_type: str,
                           evidence: dict[str, Any]) -> float:
        """计算事件置信度"""
        if event_type in ("NPC_EAT", "NPC_SLEEP", "NPC_MOVE_REGION",
                          "MUSHROOM_SPAWN", "FISH_SPAWN"):
            return 1.0

        if event_type in ("NPC_ENTER_WEAKENED", "NPC_RECOVER_WEAKENED"):
            hunger = evidence.get("hunger", 0)
            if hunger >= 80:
                return 1.0
            if hunger >= 60:
                return 0.9
            return 0.75

        if event_type in ("RESOURCE_DEPLETED", "FOREST_RECOVERED"):
            if evidence.get("depleted_forests", 0) >= 0:
                return 0.95
            return 0.85

        if event_type in ("REGION_COLLAPSE", "REGION_RECOVERY"):
            pressure = evidence.get("region_pressure", 0)
            if event_type == "REGION_COLLAPSE" and pressure >= 0.8:
                return 1.0
            if event_type == "REGION_RECOVERY" and pressure < 0.4:
                return 1.0
            return 0.9

        return 0.7

    def get_evidence_preview(self, event_id: int) -> str:
        """生成简短证据预览文本（用于live_feed显示）"""
        ev = self.get_evidence(event_id)
        if not ev:
            return ""
        parts = []
        if "hunger" in ev:
            parts.append(f"hunger={ev['hunger']}")
        if "nearby_food" in ev and ev["nearby_food"] is not None:
            parts.append(f"food_nearby={ev['nearby_food']}")
        if "region_pressure" in ev:
            parts.append(f"pressure={ev['region_pressure']}")
        if "depleted_forests" in ev:
            parts.append(f"depleted={ev['depleted_forests']}")
        if "state" in ev:
            parts.append(f"state={ev['state']}")
        return " | ".join(parts) if parts else ""

    @staticmethod
    def _count_nearby_food(npc: object, resource_mgr: object) -> Optional[int]:
        """统计NPC附近的可获取资源"""
        if not hasattr(npc, "x") or not hasattr(npc, "y"):
            return None
        nx, ny = getattr(npc, "x", 0), getattr(npc, "y", 0)
        count = 0
        for (mx, my), val in getattr(resource_mgr, "mushrooms", {}).items():
            if abs(mx - nx) <= 3 and abs(my - ny) <= 3:
                count += val if isinstance(val, int) else 1
        for (fx, fy), val in getattr(resource_mgr, "fish", {}).items():
            if abs(fx - nx) <= 3 and abs(fy - ny) <= 3:
                count += val if isinstance(val, int) else 1
        return count
