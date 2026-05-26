"""
区域追踪器 — Island Sim v1 (T-027 迁徙走廊)

追踪16个宏观区域的访问频率、压力变化、生态状态和迁徙走廊。
数据来源：真实事件记录，非预测。
"""

import os
from collections import defaultdict
from typing import Any, Optional

import yaml

from config import MIGRATION_CORRIDOR_THRESHOLD


def _load_regions() -> list[dict[str, Any]]:
    """加载区域定义"""
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "world_seed", "regions.yaml",
    )
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("regions", [])
    return []


class RegionTracker:
    """区域级统计追踪器。"""

    def __init__(self) -> None:
        self._regions = _load_regions()
        self._stats: dict[str, dict[str, Any]] = {}

        for r in self._regions:
            rid = r["id"]
            self._stats[rid] = {
                "name": r["name"],
                "visits": 0,           # NPC 进入次数
                "visitors": set(),      # 到访过的 NPC
                "depletions": 0,        # 资源耗尽次数
                "recoveries": 0,        # 恢复次数
                "collapses": 0,         # 崩溃次数
                "last_visit_tick": 0,   # 最后访问 tick
                "peak_pressure": 0.0,   # 历史最高压力
                "resource_type_counts": {},  # {resource_type: count}
            }

        # ── 迁徙走廊（T-027） ──
        self._corridor_heat: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int),
        )
        """迁徙热度: {from_region_id: {to_region_id: count}}"""
        self._last_npc_region: dict[str, Optional[str]] = {}
        """每个NPC上次所在的区域: {npc_name: region_id}"""

    def _tile_to_region_id(self, x: int, y: int) -> Optional[str]:
        """tile 坐标 → 区域ID"""
        gx, gy = x // 5, y // 5
        return self._grid_to_region_id(gx, gy)

    def _grid_to_region_id(self, gx: int, gy: int) -> Optional[str]:
        """区域网格坐标 → 区域ID"""
        for r in self._regions:
            if r["grid_x"] == gx and r["grid_y"] == gy:
                return r["id"]
        return None

    def record_collapse_at_grid(self, gx: int, gy: int) -> None:
        """按区域网格坐标记录崩溃"""
        rid = self._grid_to_region_id(gx, gy)
        if rid is None:
            return
        self._stats[rid]["collapses"] += 1

    def update_pressure_at_grid(self, gx: int, gy: int, score: float) -> None:
        """按区域网格坐标更新压力"""
        rid = self._grid_to_region_id(gx, gy)
        if rid is None:
            return
        s = self._stats[rid]
        if score > s["peak_pressure"]:
            s["peak_pressure"] = score

    def record_visit(self, x: int, y: int, npc_name: str, tick: int) -> None:
        """记录一次 NPC 进入"""
        rid = self._tile_to_region_id(x, y)
        if rid is None:
            return
        s = self._stats[rid]
        s["visits"] += 1
        s["visitors"].add(npc_name)
        if tick > s["last_visit_tick"]:
            s["last_visit_tick"] = tick

        # 追踪迁徙走廊：从上一次区域到当前区域
        prev_rid = self._last_npc_region.get(npc_name)
        if prev_rid is not None and prev_rid != rid:
            self._corridor_heat[prev_rid][rid] += 1
        self._last_npc_region[npc_name] = rid

    def record_depletion(self, x: int, y: int, rtype: str = "forest") -> None:
        """记录一次资源耗尽"""
        rid = self._tile_to_region_id(x, y)
        if rid is None:
            return
        s = self._stats[rid]
        s["depletions"] += 1
        s["resource_type_counts"][rtype] = \
            s["resource_type_counts"].get(rtype, 0) + 1

    def record_recovery(self, x: int, y: int) -> None:
        """记录一次森林恢复"""
        rid = self._tile_to_region_id(x, y)
        if rid is None:
            return
        self._stats[rid]["recoveries"] += 1

    def record_collapse(self, x: int, y: int) -> None:
        """记录一次区域崩溃"""
        rid = self._tile_to_region_id(x, y)
        if rid is None:
            return
        s = self._stats[rid]
        s["collapses"] += 1

    def update_pressure(self, x: int, y: int, score: float) -> None:
        """更新区域当前压力分"""
        rid = self._tile_to_region_id(x, y)
        if rid is None:
            return
        s = self._stats[rid]
        if score > s["peak_pressure"]:
            s["peak_pressure"] = score

    def get_most_visited(self, top_n: int = 3) -> list[dict[str, Any]]:
        """访问最频繁的区域 TOP N"""
        sorted_stats = sorted(
            self._stats.values(),
            key=lambda s: s["visits"],
            reverse=True,
        )
        return [
            {
                "name": s["name"],
                "visits": s["visits"],
                "visitor_count": len(s["visitors"]),
            }
            for s in sorted_stats[:top_n]
        ]

    def get_most_pressured(self, top_n: int = 3) -> list[dict[str, Any]]:
        """压力最高的区域 TOP N"""
        sorted_stats = sorted(
            self._stats.values(),
            key=lambda s: s["peak_pressure"],
            reverse=True,
        )
        return [
            {
                "name": s["name"],
                "peak_pressure": round(s["peak_pressure"], 2),
                "depletions": s["depletions"],
                "collapses": s["collapses"],
            }
            for s in sorted_stats[:top_n]
        ]

    def get_abandoned(self, current_tick: int,
                      abandon_threshold: int = 7200) -> list[str]:
        """长时间无人访问的区域"""
        result = []
        for rid, s in self._stats.items():
            if s["last_visit_tick"] > 0 \
                    and current_tick - s["last_visit_tick"] > abandon_threshold:
                result.append(s["name"])
        return result

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """返回完整统计快照"""
        result = {}
        for rid, s in self._stats.items():
            entry = dict(s)
            entry["visitors"] = list(entry["visitors"])
            result[rid] = entry
        return result

    # ── 迁徙走廊（T-027） ──

    def get_migration_corridors(self) -> list[dict[str, Any]]:
        """返回活跃迁徙走廊列表（按流量降序）"""
        corridors = []
        for from_rid, to_dict in self._corridor_heat.items():
            for to_rid, count in to_dict.items():
                if count >= MIGRATION_CORRIDOR_THRESHOLD:
                    from_name = self._get_region_name(from_rid)
                    to_name = self._get_region_name(to_rid)
                    corridors.append({
                        "from": from_name,
                        "to": to_name,
                        "from_id": from_rid,
                        "to_id": to_rid,
                        "traffic": count,
                    })
        corridors.sort(key=lambda c: -c["traffic"])
        return corridors

    def get_migration_corridor_report(self) -> str:
        """返回迁徙走廊报告文本"""
        corridors = self.get_migration_corridors()
        if not corridors:
            return "尚未形成稳定迁徙走廊"

        lines = [f"已形成 {len(corridors)} 条迁徙走廊："]
        for c in corridors:
            lines.append(
                f"  {c['from']} → {c['to']} ({c['traffic']} 次)"
            )
        return "\n".join(lines)

    def get_migration_flow(self, region_id: str) -> dict[str, Any]:
        """返回指定区域的迁徙流向：流入/流出"""
        outflow = dict(self._corridor_heat.get(region_id, {}))
        inflow = {}
        for from_rid, to_dict in self._corridor_heat.items():
            if region_id in to_dict:
                inflow[from_rid] = to_dict[region_id]
        return {
            "outflow": outflow,
            "inflow": inflow,
            "net_flow": sum(outflow.values()) - sum(inflow.values()),
        }

    def _get_region_name(self, rid: str) -> str:
        """rid → 区域名称"""
        for r in self._regions:
            if r["id"] == rid:
                return r.get("name", rid)
        return rid

    @property
    def regions(self) -> list[dict[str, Any]]:
        return list(self._regions)
