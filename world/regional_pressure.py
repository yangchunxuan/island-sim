"""
区域压力地图 — Island Sim v1 (T-027 地理生态层)

管理16个宏观区域(4x4)的生态状态，包含：
- 压力分计算（已有）
- 地力系统（fertility per region）
- 气候区划分
- 空间生态（压力扩散、恢复扩散）
- 生态避难所（refugia）
"""

import os
from typing import Any, Optional

import yaml

from config import (
    DAY_TICKS,
    FERTILITY_BASE_REGEN,
    FERTILITY_COLLAPSE_PENALTY,
    FERTILITY_MAX,
    FERTILITY_MIN,
    FERTILITY_RECOVERY_RATE,
    FERTILITY_TRAFFIC_DECAY,
    MAP_HEIGHT,
    MAP_WIDTH,
    REGION_SIZE,
    REFUGIA_COLLAPSE_RESISTANCE,
    REFUGIA_RECOVERY_BONUS,
    REFUGIA_THRESHOLD,
    SPATIAL_DIFFUSION_MIN,
    SPATIAL_DIFFUSION_RATE,
    SPATIAL_RECOVERY_BONUS_MAX,
    SPATIAL_RECOVERY_SPREAD,
    TileType,
)


def _load_region_data() -> list[dict[str, Any]]:
    """从 world_seed 加载区域定义"""
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "world_seed", "regions.yaml",
    )
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("regions", [])
    return []


def _humidity_to_climate(humidity: float) -> str:
    """humidity → 气候类型"""
    if humidity >= 0.7:
        return "humid"
    if humidity <= 0.35:
        return "arid"
    # 北部+高湿 = cold，否则 temperate
    return "temperate"


class RegionPressureMap:
    """区域压力图：追踪地力、气候、压力和空间生态传播"""

    REGION_COLS: int = MAP_WIDTH // REGION_SIZE   # 4
    REGION_ROWS: int = MAP_HEIGHT // REGION_SIZE  # 4

    def __init__(self, grid: list[list[TileType]]) -> None:
        self._grid = grid
        self._region_data = _load_region_data()

        # ── 压力系统（已有） ──
        self._pressure_scores: dict[tuple[int, int], float] = {}
        self._collapsed: set[tuple[int, int]] = set()
        self._last_collapse_tick: dict[tuple[int, int], int] = {}

        # ── 地力系统（T-027） ──
        self._fertility: dict[str, float] = {}  # region_id → current_fertility
        self._base_fertility: dict[str, float] = {}
        self._load_fertility()

        # ── 气候区（T-027） ──
        # region_id → climate_data
        self._climate: dict[str, dict[str, float]] = {}
        self._load_climate()

        # ── 空间生态累积量（T-027） ──
        self._neighbor_pressure_bonus: dict[str, float] = {}
        self._neighbor_recovery_bonus: dict[str, float] = {}

    # ── 初始化 ──

    def _load_fertility(self) -> None:
        """从区域定义加载基础 fertility"""
        for r in self._region_data:
            rid = r["id"]
            fert = max(FERTILITY_MIN, min(FERTILITY_MAX, r.get("fertility", 0.5)))
            self._base_fertility[rid] = fert
            self._fertility[rid] = fert  # 初始值与base相同

    def _load_climate(self) -> None:
        """根据区域 humidity + biome 分配气候区"""
        for r in self._region_data:
            rid = r["id"]
            hum = r.get("humidity", 0.5)
            climate_type = _humidity_to_climate(hum)
            temp = r.get("temperature", 0.5)

            bonus = {}
            if climate_type == "humid":
                bonus = {"mushroom": 2.0, "regrowth": 1.3, "fish": 1.2}
            elif climate_type == "arid":
                bonus = {"mushroom": 0.3, "regrowth": 0.5, "fish": 0.6}
            elif climate_type == "cold":
                bonus = {"mushroom": 0.5, "regrowth": 0.4, "fish": 0.3}
            else:  # temperate
                bonus = {"mushroom": 1.0, "regrowth": 1.0, "fish": 1.0}

            self._climate[rid] = {
                "type": climate_type,
                "humidity": hum,
                "temp": temp,
                "mushroom_bonus": bonus["mushroom"],
                "regrowth_bonus": bonus["regrowth"],
                "fish_bonus": bonus["fish"],
            }

    # ── 坐标工具 ──

    @staticmethod
    def tile_to_region(tx: int, ty: int) -> tuple[int, int]:
        """tile坐标 → 区域坐标"""
        return (tx // REGION_SIZE, ty // REGION_SIZE)

    def region_name(self, rx: int, ry: int) -> str:
        """区域可读名称"""
        rid = self._grid_to_region_id(rx, ry)
        if rid:
            for r in self._region_data:
                if r["id"] == rid:
                    return r.get("name", f"({rx},{ry})")
        return f"({rx},{ry})"

    def _grid_to_region_id(self, gx: int, gy: int) -> Optional[str]:
        """区域网格坐标 → region_id"""
        for r in self._region_data:
            if r["grid_x"] == gx and r["grid_y"] == gy:
                return r["id"]
        return None

    def _tile_to_region_id(self, tx: int, ty: int) -> Optional[str]:
        """tile坐标 → region_id"""
        return self._grid_to_region_id(tx // REGION_SIZE, ty // REGION_SIZE)

    def _neighbors(self, rx: int, ry: int) -> list[tuple[int, int]]:
        """返回相邻区域的网格坐标（上下左右）"""
        result = []
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = rx + dx, ry + dy
            if 0 <= nx < self.REGION_COLS and 0 <= ny < self.REGION_ROWS:
                result.append((nx, ny))
        return result

    # ── 地力系统 ──

    def get_fertility(self, tx: int, ty: int) -> float:
        """返回tile所在区域的当前地力"""
        rid = self._tile_to_region_id(tx, ty)
        if rid is None:
            return 0.5
        return self._fertility.get(rid, 0.5)

    def get_fertility_by_region(self, rx: int, ry: int) -> float:
        """按区域坐标返回地力"""
        rid = self._grid_to_region_id(rx, ry)
        if rid is None:
            return 0.5
        return self._fertility.get(rid, 0.5)

    def is_refugia(self, rx: int, ry: int) -> bool:
        """判断区域是否为生态避难所"""
        rid = self._grid_to_region_id(rx, ry)
        if rid is None:
            return False
        return self._fertility.get(rid, 0.0) >= REFUGIA_THRESHOLD

    def get_refugia_list(self) -> list[str]:
        """返回当前避难所区域名称列表"""
        result = []
        for r in self._region_data:
            rid = r["id"]
            fert = self._fertility.get(rid, 0.0)
            if fert >= REFUGIA_THRESHOLD:
                result.append(r["name"])
        return result

    def _process_fertility(
        self, tick: int, resource_mgr: object,
    ) -> None:
        """每帧处理地力变化：
        - 高流量 → fertility 下降
        - 无人访问 → fertility 恢复
        - collapse → fertility 永久损失
        - 长期健康 → 向 base 回归
        """
        for r in self._region_data:
            rid = r["id"]
            rx, ry = r["grid_x"], r["grid_y"]
            current = self._fertility[rid]
            base = self._base_fertility[rid]

            # 计算本区域的流量
            total_traffic = 0
            for dx in range(REGION_SIZE):
                for dy in range(REGION_SIZE):
                    tx = rx * REGION_SIZE + dx
                    ty = ry * REGION_SIZE + dy
                    if 0 <= tx < MAP_WIDTH and 0 <= ty < MAP_HEIGHT:
                        total_traffic += resource_mgr.get_traffic(tx, ty)

            # 高流量 → 地力下降
            traffic_decay = total_traffic * FERTILITY_TRAFFIC_DECAY
            current -= traffic_decay

            # collapse 惩罚（每次 collapse 永久损失 fertility）
            if (rx, ry) in self._collapsed:
                current -= FERTILITY_COLLAPSE_PENALTY / DAY_TICKS  # 分摊到每帧

            # 无人访问 → fertility 缓慢恢复
            rid_stats = self._grid_to_region_id(rx, ry)
            if rid_stats:
                current += FERTILITY_RECOVERY_RATE

            # 向 base_fertility 回归
            if current < base:
                current += FERTILITY_BASE_REGEN
            elif current > base:
                current -= FERTILITY_BASE_REGEN * 0.5

            # 邻居恢复加成
            nb_bonus = self._neighbor_recovery_bonus.get(rid, 0.0)
            current += nb_bonus

            self._fertility[rid] = max(FERTILITY_MIN, min(FERTILITY_MAX, current))

    # ── 气候系统 ──

    def get_climate_type(self, tx: int, ty: int) -> str:
        """返回tile所在区域的气候类型"""
        rid = self._tile_to_region_id(tx, ty)
        if rid is None:
            return "temperate"
        c = self._climate.get(rid, {})
        return c.get("type", "temperate")

    def get_climate_name(self, tx: int, ty: int) -> str:
        """返回tile所在区域的气候名称"""
        names = {"humid": "湿润", "arid": "干旱", "cold": "寒冷", "temperate": "温和"}
        return names.get(self.get_climate_type(tx, ty), "温和")

    def get_climate_modifier(
        self, tx: int, ty: int, resource_type: str,
    ) -> float:
        """返回气候对某类资源的生成倍率"""
        rid = self._tile_to_region_id(tx, ty)
        if rid is None:
            return 1.0
        c = self._climate.get(rid, {})
        key_map = {
            "mushroom": "mushroom_bonus",
            "fish": "fish_bonus",
            "forest": "regrowth_bonus",
        }
        key = key_map.get(resource_type, "regrowth_bonus")
        return c.get(key, 1.0)

    # ── 空间生态（压力扩散 + 恢复扩散） ──

    def _spread_pressure(self) -> None:
        """高压力 → 相邻区域的 pressure 扩散"""
        neighbor_pressure: dict[str, float] = {}
        neighbor_recovery: dict[str, float] = {}

        for r in self._region_data:
            rid = r["id"]
            rx, ry = r["grid_x"], r["grid_y"]
            score = self._pressure_scores.get((rx, ry), 0.0)

            if score > SPATIAL_DIFFUSION_MIN:
                spread = score * SPATIAL_DIFFUSION_RATE
                for nx, ny in self._neighbors(rx, ry):
                    nid = self._grid_to_region_id(nx, ny)
                    if nid:
                        neighbor_pressure[nid] = \
                            neighbor_pressure.get(nid, 0.0) + spread

            if score < 0.3:  # 低压力 = 恢复区 → 帮助邻居
                recovery_spread = (1.0 - score) * SPATIAL_RECOVERY_SPREAD
                for nx, ny in self._neighbors(rx, ry):
                    nid = self._grid_to_region_id(nx, ny)
                    if nid:
                        neighbor_recovery[nid] = \
                            neighbor_recovery.get(nid, 0.0) + recovery_spread

        self._neighbor_pressure_bonus = neighbor_pressure
        self._neighbor_recovery_bonus = {
            rid: min(SPATIAL_RECOVERY_BONUS_MAX, v)
            for rid, v in neighbor_recovery.items()
        }

    # ── 压力计算 ──

    def update(
        self, tick: int, resource_mgr: object,
        time_system: object = None,
    ) -> list[tuple[str, tuple[int, int]]]:
        """更新所有区域压力值，返回新发生的崩溃/恢复事件"""
        events: list[tuple[str, tuple[int, int]]] = []

        # 1. 空间生态扩散
        self._spread_pressure()

        # 2. 地力更新（基于流量）
        self._process_fertility(tick, resource_mgr)

        for ry in range(self.REGION_ROWS):
            for rx in range(self.REGION_COLS):
                r = (rx, ry)
                score = self._calc_score(rx, ry, resource_mgr)
                self._pressure_scores[r] = score

                # 避难所区域有额外的 collapse 抗性
                collapse_threshold = 0.8
                if self.is_refugia(rx, ry):
                    collapse_threshold += REFUGIA_COLLAPSE_RESISTANCE

                if score > collapse_threshold and r not in self._collapsed:
                    self._collapsed.add(r)
                    self._last_collapse_tick[r] = tick
                    events.append(("REGION_COLLAPSE", r))
                elif score < 0.4 and r in self._collapsed:
                    self._collapsed.discard(r)
                    events.append(("REGION_RECOVERY", r))
        return events

    def _calc_score(self, rx: int, ry: int, resource_mgr: object) -> float:
        """计算单个区域的压力值 (0.0=健康, 1.0=崩溃)"""
        total_footfall = 0
        depleted = 0
        forest_tiles = 0

        for dx in range(REGION_SIZE):
            for dy in range(REGION_SIZE):
                tx = rx * REGION_SIZE + dx
                ty = ry * REGION_SIZE + dy
                if not (0 <= tx < MAP_WIDTH and 0 <= ty < MAP_HEIGHT):
                    continue
                total_footfall += resource_mgr.get_traffic(tx, ty)
                if resource_mgr.is_depleted(tx, ty):
                    depleted += 1
                if self._grid[ty][tx] == TileType.FOREST:
                    forest_tiles += 1

        activity = min(1.0, total_footfall / 100.0)
        depletion = min(1.0, depleted / max(1, forest_tiles))

        # 地力影响：fertility 低 → 压力更大
        rid = self._grid_to_region_id(rx, ry)
        fert = self._fertility.get(rid, 0.5)
        fertility_factor = 1.0 + (0.5 - fert)  # fert 0.2 → factor 1.3; fert 0.8 → factor 0.7

        # 空间生态：来自邻居的压力
        nb_pressure = self._neighbor_pressure_bonus.get(rid, 0.0)

        return min(1.0, (activity * 0.4 + depletion * 0.4) * fertility_factor + nb_pressure)

    # ── 对资源的影响 ──

    def get_spawn_multiplier(self, tx: int, ty: int) -> float:
        """压力+地力+气候对资源生成率的综合倍率（居中于1.0）"""
        rid = self._tile_to_region_id(tx, ty)
        if rid is None:
            return 1.0

        score = self.get_score(tx, ty)
        # 压力影响：高压→低生成 (score 0.0→1.0 maps to 1.5→0.5)
        pressure_factor = 1.5 - score

        # 地力微调：fert 0.0→0.7, 1.0→1.3
        fert = self.get_fertility(tx, ty)
        fert_factor = 0.7 + fert * 0.6

        return max(0.1, pressure_factor * fert_factor)

    def get_regrowth_multiplier(self, tx: int, ty: int) -> float:
        """压力+地力+气候对森林恢复速度的综合倍率"""
        rid = self._tile_to_region_id(tx, ty)
        if rid is None:
            return 1.0

        score = self.get_score(tx, ty)
        # 压力影响：高压→慢恢复 (score 0.0→1.0 maps to 1.2→0.3)
        pressure_factor = max(0.2, 1.2 - score)

        fert = self.get_fertility(tx, ty)
        fert_factor = 0.7 + fert * 0.6  # fert 0.0→0.7, 1.0→1.3

        # 避难所加成
        rx, ry = self.tile_to_region(tx, ty)
        refugia_bonus = REFUGIA_RECOVERY_BONUS if self.is_refugia(rx, ry) else 1.0

        # 气候加成
        climate_mult = self.get_climate_modifier(tx, ty, "forest")

        return max(0.1, pressure_factor * fert_factor * refugia_bonus * climate_mult)

    def get_score(self, tx: int, ty: int) -> float:
        """返回tile所在区域的压力值"""
        r = self.tile_to_region(tx, ty)
        return self._pressure_scores.get(r, 0.0)

    def get_top_pressure(self, n: int = 3) -> list[tuple[tuple[int, int], float]]:
        """返回压力最高的N个区域"""
        scores = [(r, self._pressure_scores.get(r, 0.0))
                  for ry in range(self.REGION_ROWS)
                  for rx in range(self.REGION_COLS)
                  for r in [(rx, ry)]]
        scores.sort(key=lambda x: -x[1])
        return scores[:n]

    # ── 地理报告数据 ──

    def get_fertility_report(self) -> list[dict[str, Any]]:
        """返回各地 fertility 状态报告"""
        result = []
        for r in self._region_data:
            rid = r["id"]
            result.append({
                "name": r["name"],
                "base_fertility": round(self._base_fertility.get(rid, 0.5), 2),
                "current_fertility": round(self._fertility.get(rid, 0.5), 2),
                "trend": self._get_fertility_trend(rid),
            })
        result.sort(key=lambda x: -x["current_fertility"])
        return result

    def get_climate_report(self) -> list[dict[str, Any]]:
        """返回各地气候报告"""
        result = []
        for r in self._region_data:
            rid = r["id"]
            c = self._climate.get(rid, {})
            result.append({
                "name": r["name"],
                "type": c.get("type", "temperate"),
                "humidity": c.get("humidity", 0.5),
                "mushroom_bonus": c.get("mushroom_bonus", 1.0),
            })
        return result

    def _get_fertility_trend(self, rid: str) -> str:
        """fertility 趋势判断"""
        current = self._fertility.get(rid, 0.5)
        base = self._base_fertility.get(rid, 0.5)
        diff = current - base
        if diff > 0.05:
            return "increasing"
        elif diff < -0.05:
            return "declining"
        return "stable"

    @property
    def collapsed_regions(self) -> set[tuple[int, int]]:
        return self._collapsed
