"""
Summary Layer — Simulation OS 上下文压缩 (T-032)

提供 WorldSummary 类，负责生成世界状态的快照摘要（YAML 格式），
供 Agent 读取，无需解析原始日志。
"""

from typing import Any

import yaml


class WorldSummary:
    """世界状态摘要生成器

    用法:
        data = WorldSummary.generate(resource_mgr, pressure_map, npcs, time_system)
        WorldSummary.write_summary("path/to/summary.yaml", data)
    """

    @staticmethod
    def generate(
        resource_mgr,
        pressure_map,
        npcs: list,
        time_system,
        alerts: list | None = None,
    ) -> dict[str, Any]:
        """生成当前世界状态的快照摘要

        参数:
            resource_mgr: ResourceManager 实例
            pressure_map: RegionPressureMap 实例
            npcs: NPC 对象列表
            time_system: TimeSystem 实例
            alerts: 可选的 Alert 列表（来自 AlertManager）

        返回:
            结构化的 YAML 可序列化 dict
        """
        tick = time_system._tick_count if hasattr(time_system, "_tick_count") else 0
        day = time_system.get_day_count()
        season = time_system.get_season()

        # ── 生态压力（TOP 3 高压区域） ──
        top_pressures = pressure_map.get_top_pressure(n=3)
        ecology_pressure = [
            {"region": list(r), "score": round(s, 3)}
            for r, s in top_pressures
        ]

        # ── 地力数据 ──
        fertility_report = pressure_map.get_fertility_report()
        avg_fertility = (
            round(
                sum(e["current_fertility"] for e in fertility_report)
                / len(fertility_report),
                4,
            )
            if fertility_report
            else 0.0
        )

        # ── 食物供应 ──
        total_food = resource_mgr.total_food_remaining()
        forest_count = len(resource_mgr.available_forests())
        mushroom_count = len(resource_mgr.available_mushrooms())
        fish_count = len(resource_mgr.available_fish())

        # ── NPC 状态 ──
        alive = 0
        weakened = 0
        total_hunger = 0.0
        for n in npcs:
            state = n.get_state()
            if state != "DEAD":
                alive += 1
            if getattr(n, "_weakened", False):
                weakened += 1
            total_hunger += getattr(n, "hunger", 0)

        avg_hunger = round(total_hunger / len(npcs), 1) if npcs else 0.0

        # ── 迁徙趋势（基于区域压力） ──
        migration_trend = "stable"
        if top_pressures:
            highest_score = top_pressures[0][1]
            if highest_score > 0.8:
                migration_trend = "outward_pressure"
            elif highest_score > 0.5:
                migration_trend = "mild_pressure"

        result: dict[str, Any] = {
            "tick": tick,
            "day": day,
            "season": season,
            "ecology_pressure": ecology_pressure,
            "avg_fertility": avg_fertility,
            "food_supply": {
                "forests": forest_count,
                "mushrooms": mushroom_count,
                "fish": fish_count,
                "total": total_food,
            },
            "migration_trend": migration_trend,
            "npc_status": {
                "alive": alive,
                "weakened": weakened,
                "avg_hunger": avg_hunger,
            },
        }

        # ── 可选：附加活跃警报 ——
        if alerts:
            result["top_alerts"] = [
                {
                    "type": a.type.value,
                    "severity": a.severity.value,
                    "data": a.data,
                    "tick": a.tick,
                }
                for a in alerts
            ]

        return result

    @staticmethod
    def write_summary(path: str, data: dict[str, Any]) -> None:
        """将摘要数据写入 YAML 文件"""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
