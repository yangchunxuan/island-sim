"""
Alert System — Simulation OS 基础设施 (T-032)

提供 AlertType / AlertSeverity 枚举、Alert 数据类和 AlertManager 管理器。
AlertManager 负责监控 world state 并在满足条件时生成 Alert。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AlertType(Enum):
    """警报类型枚举"""
    ECO_COLLAPSE = "eco_collapse"
    FOOD_SHORTAGE = "food_shortage"
    MIGRATION = "migration"
    NPC_CONFLICT = "npc_conflict"
    REGION_COLLAPSE = "region_collapse"
    REGRESSION_DETECTED = "regression_detected"
    FERTILITY_CRISIS = "fertility_crisis"


class AlertSeverity(Enum):
    """警报严重级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Alert:
    """单个警报数据"""
    type: AlertType
    severity: AlertSeverity
    data: dict = field(default_factory=dict)
    tick: int = 0
    target_agents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "data": self.data,
            "tick": self.tick,
            "target_agents": self.target_agents,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Alert":
        return cls(
            type=AlertType(d["type"]),
            severity=AlertSeverity(d["severity"]),
            data=d.get("data", {}),
            tick=d.get("tick", 0),
            target_agents=d.get("target_agents", []),
        )


class AlertManager:
    """警报管理器 — 监控世界状态，生成警报

    内部状态跨 tick 保留（如 REGION_COLLAPSE 的连续计数），
    每次调用 check_alerts 返回本轮新触发的警报列表。
    """

    REGION_COLLAPSE_TICKS: int = 100
    """REGION_COLLAPSE 触发所需连续高压 tick 数"""

    def __init__(self):
        self._region_pressure_ticks: dict[tuple[int, int], int] = {}
        self._region_alerted: set[tuple[int, int]] = set()

    def check_alerts(
        self,
        resource_mgr,
        pressure_map,
        npcs: list,
        time_system,
    ) -> list[Alert]:
        """检查当前世界状态，返回新触发的警报列表"""
        alerts: list[Alert] = []

        tick = time_system._tick_count if hasattr(time_system, "_tick_count") else 0
        npc_count = len(npcs)

        # ── 获取 fertility 报告 ──
        fertility_report = pressure_map.get_fertility_report()

        # ── ECO_COLLAPSE: 所有区域 fertility ≤ 0.3 ──
        self._check_eco_collapse(fertility_report, tick, alerts)

        # ── FOOD_SHORTAGE: total_food < npc_count * 2 ──
        self._check_food_shortage(resource_mgr, npc_count, tick, alerts)

        # ── REGION_COLLAPSE: 某区域 pressure > 0.9 连续 100 tick ──
        self._check_region_collapse(pressure_map, tick, alerts)

        # ── FERTILITY_CRISIS: 平均 fertility < 0.2 ──
        self._check_fertility_crisis(fertility_report, tick, alerts)

        return alerts

    def _check_eco_collapse(self, fertility_report: list[dict], tick: int, alerts: list[Alert]) -> None:
        if not fertility_report:
            return
        all_low = all(entry["current_fertility"] <= 0.3 for entry in fertility_report)
        if all_low:
            alerts.append(Alert(
                type=AlertType.ECO_COLLAPSE,
                severity=AlertSeverity.CRITICAL,
                data={
                    "fertilities": {
                        e["name"]: e["current_fertility"] for e in fertility_report
                    },
                },
                tick=tick,
            ))

    def _check_food_shortage(self, resource_mgr, npc_count: int, tick: int, alerts: list[Alert]) -> None:
        if npc_count == 0:
            return
        total_food = resource_mgr.total_food_remaining()
        threshold = npc_count * 2
        if total_food < threshold:
            alerts.append(Alert(
                type=AlertType.FOOD_SHORTAGE,
                severity=AlertSeverity.HIGH,
                data={
                    "total_food": total_food,
                    "npc_count": npc_count,
                    "threshold": threshold,
                },
                tick=tick,
            ))

    def _check_region_collapse(self, pressure_map, tick: int, alerts: list[Alert]) -> None:
        # Check all regions via get_top_pressure
        # get_top_pressure(n) returns list[tuple[tuple[int, int], float]]
        top_all = pressure_map.get_top_pressure(n=16)
        updated_keys = set()

        for (rx, ry), score in top_all:
            key = (rx, ry)
            updated_keys.add(key)

            if score > 0.9:
                self._region_pressure_ticks[key] = self._region_pressure_ticks.get(key, 0) + 1

                if (
                    self._region_pressure_ticks[key] >= self.REGION_COLLAPSE_TICKS
                    and key not in self._region_alerted
                ):
                    region_name = pressure_map.region_name(rx, ry)
                    alerts.append(Alert(
                        type=AlertType.REGION_COLLAPSE,
                        severity=AlertSeverity.HIGH,
                        data={
                            "region": [rx, ry],
                            "region_name": region_name,
                            "pressure": score,
                            "duration": self._region_pressure_ticks[key],
                        },
                        tick=tick,
                    ))
                    self._region_alerted.add(key)
            else:
                # Pressure is back down — reset tracking for this region
                self._region_pressure_ticks.pop(key, None)
                self._region_alerted.discard(key)

        # Clean up any stale keys for regions that no longer appear
        for key in list(self._region_pressure_ticks.keys()):
            if key not in updated_keys:
                self._region_pressure_ticks.pop(key, None)
                self._region_alerted.discard(key)

    def _check_fertility_crisis(self, fertility_report: list[dict], tick: int, alerts: list[Alert]) -> None:
        if not fertility_report:
            return
        avg_fertility = sum(e["current_fertility"] for e in fertility_report) / len(fertility_report)
        if avg_fertility < 0.2:
            alerts.append(Alert(
                type=AlertType.FERTILITY_CRISIS,
                severity=AlertSeverity.CRITICAL,
                data={
                    "average_fertility": round(avg_fertility, 4),
                    "region_count": len(fertility_report),
                },
                tick=tick,
            ))
