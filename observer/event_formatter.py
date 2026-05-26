"""
事件格式化器 — Island Sim v1

将原始事件转为真实观察语言。
模板化 + 数据驱动。
禁止 LLM 生成。
"""

import os
from typing import Any, Optional

import yaml


def _load_regions() -> list[dict[str, Any]]:
    """从 world_seed/regions.yaml 加载区域数据"""
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "world_seed", "regions.yaml",
    )
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("regions", [])
    return []


def _coord_to_region_name(
    x: int, y: int,
    regions: list[dict[str, Any]],
) -> str:
    """将 tile 坐标映射到区域名称"""
    grid_x = x // 5
    grid_y = y // 5
    for r in regions:
        if r["grid_x"] == grid_x and r["grid_y"] == grid_y:
            return r["name"]
    return f"({x},{y})"


class EventFormatter:
    """事件格式化器。模板化 + 数据驱动。"""

    # 事件类型 → 消息模板
    TEMPLATES: dict[str, str] = {
        "NPC_EAT": "{npc} consumed food at {region}",
        "NPC_SLEEP": "{npc} rested at {region}",
        "NPC_ENTER_WEAKENED": "{npc} weakened at {region} (hunger={hunger})",
        "NPC_RECOVER_WEAKENED": "{npc} recovered from weakened state at {region}",
        "NPC_MOVE_REGION": "{npc} moved from {origin} to {region}",
        "RESOURCE_DEPLETED": "{region} resource cluster depleted ({rtype})",
        "FOREST_RECOVERED": "{region} forest cluster recovered",
        "MUSHROOM_SPAWN": "mushroom appeared at {region}",
        "FISH_SPAWN": "fish appeared at {region}",
        "REGION_COLLAPSE": "{region} ecosystem collapsed",
        "REGION_RECOVERY": "{region} ecosystem recovered",
        "NPC_BEHAVIOR_PROFILE": "{npc} behavior profile recorded",
        # T-027 地理事件
        "GEO_FERTILE_REGION": "[GEOGRAPHY] fertile region detected",
        "GEO_BARREN_REGION": "[GEOGRAPHY] barren region detected",
        "GEO_REFUGIA_ACTIVE": "[ECOLOGY] refugia zones active",
        "GEO_MIGRATION_CORRIDOR": "[MIGRATION] migration corridor forming",
        "GEOGRAPHY_REPORT": "[GEOGRAPHY] geography analysis complete",
    }

    # 事件类型 → 等级映射
    LEVEL_MAP: dict[str, str] = {
        "REGION_COLLAPSE": "CRITICAL",
        "NPC_ENTER_WEAKENED": "WARNING",
        "RESOURCE_DEPLETED": "WARNING",
        "REGION_RECOVERY": "INFO",
        "FOREST_RECOVERED": "INFO",
        "NPC_EAT": "INFO",
        "NPC_SLEEP": "INFO",
        "NPC_MOVE_REGION": "MOVEMENT",
        "NPC_RECOVER_WEAKENED": "INFO",
        "MUSHROOM_SPAWN": "ECOLOGY",
        "FISH_SPAWN": "ECOLOGY",
        "NPC_BEHAVIOR_PROFILE": "INFO",
        # T-027 地理事件
        "GEO_FERTILE_REGION": "INFO",
        "GEO_BARREN_REGION": "WARNING",
        "GEO_REFUGIA_ACTIVE": "INFO",
        "GEO_MIGRATION_CORRIDOR": "INFO",
        "GEOGRAPHY_REPORT": "INFO",
    }

    def __init__(self) -> None:
        self._regions: list[dict[str, Any]] = _load_regions()

    def format(self, event: dict[str, Any]) -> str:
        """将原始事件格式化为观察文本"""
        et = event["event_type"]
        template = self.TEMPLATES.get(et)
        if template is None:
            return f"[DATA] {et} at {event.get('position', '?')}"

        args = self._extract_args(event)
        try:
            return template.format(**args)
        except KeyError:
            return f"[DATA] {et} ({event.get('position', '?')})"

    def get_level(self, event: dict[str, Any]) -> str:
        """返回事件对应等级"""
        return self.LEVEL_MAP.get(event["event_type"], "INFO")

    def get_region_name(self, event: dict[str, Any]) -> str:
        """返回事件发生区域名称"""
        pos = event.get("position")
        if pos and len(pos) == 2:
            return _coord_to_region_name(pos[0], pos[1], self._regions)
        return "?"

    def format_with_meta(
        self,
        event: dict[str, Any],
        event_id: int = -1,
        confidence: float = 1.0,
        evidence_preview: str = "",
    ) -> dict[str, Any]:
        """格式化事件并附带元数据(event_id/confidence/region/evidence)"""
        message = self.format(event)
        region = self.get_region_name(event)

        return {
            "message": message,
            "event_id": event_id,
            "confidence": confidence,
            "level": self.get_level(event),
            "region": region,
            "evidence_preview": evidence_preview,
        }

    def _extract_args(self, event: dict[str, Any]) -> dict[str, str]:
        """从事件中提取模板参数"""
        details = event.get("details", {}) or {}
        pos = event.get("position")
        x, y = pos if pos and len(pos) == 2 else (0, 0)

        return {
            "npc": event.get("npc", "unknown"),
            "region": _coord_to_region_name(x, y, self._regions),
            "origin": details.get("from", "?"),
            "rtype": details.get("type", "unknown"),
            "hunger": str(details.get("hunger", "?")),
        }
