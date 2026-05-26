"""
资源管理模块 — 生态循环系统 v2

管理森林食物、蘑菇生命周期、鱼类资源、资源热点、人流量追踪。
T-017: 从"有限消耗"升级为"动态生态循环"。
"""

import random
from typing import Optional

from config import (
    FISH_LIFETIME,
    FISH_SPAWN_CHANCE,
    FISH_SPAWN_NIGHT_REDUCTION,
    FOOD_PER_FOREST,
    FOREST_REGROWTH_DAYS,
    HOTSPOT_FISH_MULT,
    HOTSPOT_MUSHROOM_MULT,
    MUSHROOM_FRESH_DURATION,
    MUSHROOM_NUTRITION_FRESH,
    MUSHROOM_NUTRITION_OLD,
    MUSHROOM_OLD_DURATION,
    MUSHROOM_ROTTEN_DURATION,
    MUSHROOM_SPAWN_CHANCE,
    MUSHROOM_SPAWN_NIGHT_MULT,
    TRAFFIC_DECAY,
    TRAFFIC_HIGH_THRESHOLD,
    TRAFFIC_REGROWTH_PENALTY,
    DAY_TICKS,
    TileType,
)

# ── T-031 FR-001 Stage 2b: 蘑菇肥力动态 ──
# fertility参数来自 ecology_rules.yaml
FERTILITY_REGEN_THRESHOLD = 0.3       # fertility高于此值蘑菇才能再生
FERTILITY_COST_PER_REGEN = 0.1        # 每次蘑菇再生消耗的fertility
FERTILITY_NATURAL_RECOVERY = 0.02     # 无再生时fertility自然恢复 — FR-001a: 0.005→0.02
MUSHROOM_FERTILITY_BASE_RATE = 0.03   # 蘑菇再生基础概率（ecology_rules.yaml spawn_base_rate）


class ResourceManager:
    """生态循环管理器：森林恢复、蘑菇/鱼生命周期、资源热点、人流量"""

    def __init__(self, grid: list[list[TileType]]) -> None:
        self._grid = grid
        # ── 森林食物 ──
        self._food_stock: dict[tuple[int, int], int] = {}
        self._depleted: set[tuple[int, int]] = set()
        # 恢复定时器：(x,y) -> remaining_ticks
        self._regrowth_timer: dict[tuple[int, int], int] = {}

        # ── 蘑菇系统 ──
        self._mushrooms: dict[tuple[int, int], dict] = {}
        # 候选蘑菇生成tile（FOREST旁2格内可行走tile）
        self._mushroom_spawn_zones: list[tuple[int, int]] = []
        # 蘑菇热点倍率（预计算）
        self._mushroom_hotspot: dict[tuple[int, int], float] = {}

        # ── 鱼类系统 ──
        self._fish: dict[tuple[int, int], dict] = {}
        # 候选鱼生成tile（WATER旁的SAND tile）
        self._fish_spawn_zones: list[tuple[int, int]] = []
        # 鱼类热点倍率（预计算）
        self._fish_hotspot: dict[tuple[int, int], float] = {}

        # ── 人流量追踪 ──
        self._footfall: dict[tuple[int, int], int] = {}  # 累积访问（永不衰减）
        self._recent_traffic: dict[tuple[int, int], float] = {}  # 近期流量（衰减）
        self._regrowth_delayed: set[tuple[int, int]] = set()  # 已被延迟一次的森林

        # ── 生态帧计数器（NPC多次调用去重用） ──
        self._eco_call_count: int = 0

        # ── 区域压力参考（T-019） ──
        self._pressure_map: object = None

        # ── 时间系统参考（T-027 季节） ──
        self._time_system: object = None

        # ── 生态迁移（T-022） ──
        self._eco_tick: int = 0  # 生态帧计数器（去重后的实际计数）

        # ── T-031 FR-001 Stage 2b: 蘑菇肥力动态 ──
        # current_fertility[region_id] = 当前fertility，从RegionPressureMap.base_fertility拷贝
        self.current_fertility: dict[str, float] = {}
        # tile坐标 → region_id 的预计算映射（在set_pressure_map时初始化）
        self._tile_region_map: dict[tuple[int, int], str] = {}
        # 每tick有再生的区域集合（在update开始时重置）
        self._spawned_regions: set = set()

        self._init_food(grid)
        self._init_spawn_zones(grid)
        self._init_hotspots(grid)

    # ══════════════════════════════════════════
    # 初始化
    # ══════════════════════════════════════════

    def _init_food(self, grid: list[list[TileType]]) -> None:
        """为每个FOREST tile分配初始食物储量"""
        for y in range(len(grid)):
            for x in range(len(grid[y])):
                if grid[y][x] == TileType.FOREST:
                    self._food_stock[(x, y)] = FOOD_PER_FOREST

    def _init_spawn_zones(self, grid: list[list[TileType]]) -> None:
        """预计算蘑菇和鱼的候选生成区域"""
        for y in range(len(grid)):
            for x in range(len(grid[y])):
                tile = grid[y][x]

                # 蘑菇候选：FOREST旁2格内的GRASS/SAND
                if tile in (TileType.GRASS, TileType.SAND):
                    for dx in range(-2, 3):
                        for dy in range(-2, 3):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < len(grid[y]) and 0 <= ny < len(grid):
                                if grid[ny][nx] == TileType.FOREST:
                                    self._mushroom_spawn_zones.append((x, y))
                                    break
                        else:
                            continue
                        break

                # 鱼类候选：WATER旁的SAND tile
                if tile == TileType.SAND:
                    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < len(grid[y]) and 0 <= ny < len(grid):
                            if grid[ny][nx] == TileType.WATER:
                                self._fish_spawn_zones.append((x, y))
                                break

    def _init_hotspots(self, grid: list[list[TileType]]) -> None:
        """预计算资源热点倍率（基于坐标哈希产生区域差异）"""
        # 蘑菇热点：FOREST附近某些区域概率更高
        for x, y in self._mushroom_spawn_zones:
            h = hash((x * 7 + 13, y * 11 + 5)) & 0xFFFF
            self._mushroom_hotspot[(x, y)] = 1.0 + (h % 100) / 100.0 * 2.0

        # 鱼类热点：某些海岸概率更高
        for x, y in self._fish_spawn_zones:
            h = hash((x * 3 + 7, y * 5 + 11)) & 0xFFFF
            self._fish_hotspot[(x, y)] = 1.0 + (h % 100) / 100.0 * 1.5

    # ── 生态迁移（T-022） ──

    def _update_hotspot_drift(self) -> None:
        """根据区域压力调整热点倍率：高压区热点漂走，低压区形成新热点"""
        pm_spawn = getattr(self._pressure_map, 'get_spawn_multiplier', None)
        if pm_spawn is None:
            return
        for zone in self._mushroom_spawn_zones:
            x, y = zone
            target = pm_spawn(x, y)  # 0.5/1.0/1.5
            current = self._mushroom_hotspot.get(zone, 1.0)
            self._mushroom_hotspot[zone] = max(0.3, min(3.0, current + (target - current) * 0.02))
        for zone in self._fish_spawn_zones:
            x, y = zone
            target = pm_spawn(x, y)
            current = self._fish_hotspot.get(zone, 1.0)
            self._fish_hotspot[zone] = max(0.3, min(3.0, current + (target - current) * 0.02))

    # ══════════════════════════════════════════
    # 森林食物系统
    # ══════════════════════════════════════════

    def get_food_amount(self, x: int, y: int) -> int:
        """返回指定FOREST tile的剩余食物量"""
        return self._food_stock.get((x, y), 0)

    def is_depleted(self, x: int, y: int) -> bool:
        """指定坐标的FOREST是否已耗尽"""
        return (x, y) in self._depleted

    def available_forests(self) -> list[tuple[int, int]]:
        """返回还有剩余食物的FOREST坐标列表"""
        return [(x, y) for (x, y), stock in self._food_stock.items() if stock > 0]

    def total_food_remaining(self) -> int:
        """地图上所有FOREST的剩余食物总量"""
        return sum(self._food_stock.values())

    def forest_count(self) -> int:
        """地图上FOREST tile总数（含已耗尽）"""
        return len(self._food_stock)

    def collect(self, x: int, y: int) -> int:
        """采集1单位森林食物。返回实际获得量（0或1）。"""
        if (x, y) in self._depleted or (x, y) not in self._food_stock:
            return 0

        stock = self._food_stock[(x, y)]
        if stock <= 0:
            self._depleted.add((x, y))
            print(f"[WORLD] Forest ({x},{y}) depleted")
            return 0

        self._food_stock[(x, y)] = stock - 1
        if self._food_stock[(x, y)] <= 0:
            self._depleted.add((x, y))
            print(f"[WORLD] Forest ({x},{y}) depleted")
            base = FOREST_REGROWTH_DAYS * DAY_TICKS
            pm = getattr(self._pressure_map, 'get_regrowth_multiplier', None)
            if pm:
                base = int(base / pm(x, y))
            self._regrowth_timer[(x, y)] = base
        return 1

    # ── 森林恢复 ──

    def _process_regrowth(self) -> None:
        """处理depleted森林的恢复计时（低压区域优先恢复，实现生态迁移）"""
        season_mult = self._get_season_mult("forest")
        expired = []
        for pos, ticks in self._regrowth_timer.items():
            self._regrowth_timer[pos] = ticks - season_mult
            if self._regrowth_timer[pos] <= 0:
                expired.append(pos)

        # T-022: 低压区域优先恢复（生态迁移：恢复波从健康区扩散）
        pm = getattr(self._pressure_map, 'get_score', None)
        if pm and len(expired) > 1:
            expired.sort(key=lambda pos: pm(pos[0], pos[1]))

        for pos in expired:
            x, y = pos
            # 高脚流量延迟恢复（每个森林仅延迟一次）
            footfall = self._footfall.get(pos, 0)
            if footfall > TRAFFIC_HIGH_THRESHOLD and pos not in self._regrowth_delayed:
                self._regrowth_timer[pos] = FOREST_REGROWTH_DAYS * DAY_TICKS // 2
                self._regrowth_delayed.add(pos)
                print(f"[ECO] Forest ({x},{y}) regrowth delayed by footfall ({footfall})")
                continue

            self._food_stock[pos] = FOOD_PER_FOREST
            self._depleted.discard(pos)
            del self._regrowth_timer[pos]
            print(f"[ECO] Forest ({x},{y}) regrown!")

    # ══════════════════════════════════════════
    # 蘑菇系统
    # ══════════════════════════════════════════

    def _get_mushroom_stage(self, mush: dict) -> str:
        """返回蘑菇当前阶段名称"""
        age = mush["age"]
        if age < 10:
            return "spawned"
        elif age < 10 + MUSHROOM_FRESH_DURATION:
            return "fresh"
        elif age < 10 + MUSHROOM_FRESH_DURATION + MUSHROOM_OLD_DURATION:
            return "old"
        elif age < 10 + MUSHROOM_FRESH_DURATION + MUSHROOM_OLD_DURATION + MUSHROOM_ROTTEN_DURATION:
            return "rotten"
        return "gone"

    def is_edible_mushroom(self, x: int, y: int) -> bool:
        """指定坐标是否有可食用的蘑菇（fresh或old）"""
        mush = self._mushrooms.get((x, y))
        if mush is None:
            return False
        stage = self._get_mushroom_stage(mush)
        return stage in ("fresh", "old")

    def collect_mushroom(self, x: int, y: int) -> int:
        """采集蘑菇。返回可减少的饥饿值（0表示不可食用或无蘑菇）。"""
        mush = self._mushrooms.get((x, y))
        if mush is None:
            return 0
        stage = self._get_mushroom_stage(mush)
        if stage == "fresh":
            nutrition = MUSHROOM_NUTRITION_FRESH
        elif stage == "old":
            nutrition = MUSHROOM_NUTRITION_OLD
        else:
            return 0  # spawned/rotten不可食用
        del self._mushrooms[(x, y)]
        return nutrition

    def available_mushrooms(self) -> list[tuple[int, int, str]]:
        """返回所有可食用蘑菇列表：(x, y, stage)"""
        result = []
        for pos, mush in list(self._mushrooms.items()):
            stage = self._get_mushroom_stage(mush)
            if stage in ("fresh", "old"):
                x, y = pos
                result.append((x, y, stage))
        return result

    def _process_mushrooms(self) -> None:
        """处理蘑菇：生成新蘑菇 + 生命周期推进"""
        # ── 生成 ──
        is_night = self._is_night_time()
        spawn_chance = MUSHROOM_SPAWN_CHANCE
        if is_night:
            spawn_chance *= MUSHROOM_SPAWN_NIGHT_MULT

        pressure_mult = getattr(self._pressure_map, 'get_spawn_multiplier', None)
        season_mult = self._get_season_mult("mushroom")

        for zone in self._mushroom_spawn_zones:
            if zone in self._mushrooms:
                continue  # 已有蘑菇

            # T-031: fertility检查 — fertility低于阈值则无法再生
            rid = self._tile_region_map.get(zone)
            if rid is None or self.current_fertility.get(rid, 0) <= FERTILITY_REGEN_THRESHOLD:
                continue

            fert_factor = self.current_fertility[rid] * MUSHROOM_FERTILITY_BASE_RATE

            # 热点倍率
            hotspot = self._mushroom_hotspot.get(zone, 1.0)
            p_mult = pressure_mult(zone[0], zone[1]) if pressure_mult else 1.0
            if random.random() < spawn_chance * hotspot * p_mult * season_mult * fert_factor:
                self._mushrooms[zone] = {"age": 0}
                # T-031: 再生消耗fertility
                self.current_fertility[rid] = max(0.0, self.current_fertility[rid] - FERTILITY_COST_PER_REGEN)
                self._spawned_regions.add(rid)
                x, y = zone
                print(f"[ECO] Mushroom spawned at ({x},{y})")

        # ── 生命周期推进 ──
        expired = []
        for pos, mush in self._mushrooms.items():
            mush["age"] += 1
            if self._get_mushroom_stage(mush) == "gone":
                expired.append(pos)
        for pos in expired:
            x, y = pos
            print(f"[ECO] Mushroom at ({x},{y}) disappeared")
            del self._mushrooms[pos]

    # ══════════════════════════════════════════
    # 鱼类系统
    # ══════════════════════════════════════════

    def is_edible_fish(self, x: int, y: int) -> bool:
        """指定坐标是否有可食用的鱼"""
        fish = self._fish.get((x, y))
        return fish is not None and fish["age"] < FISH_LIFETIME

    def collect_fish(self, x: int, y: int) -> int:
        """采集鱼。返回可减少的饥饿值（0表示无鱼）。"""
        fish = self._fish.get((x, y))
        if fish is None:
            return 0
        from config import FISH_NUTRITION
        nutrition = FISH_NUTRITION
        del self._fish[(x, y)]
        return nutrition

    def available_fish(self) -> list[tuple[int, int]]:
        """返回所有可食用鱼坐标列表"""
        return [
            pos for pos, fish in self._fish.items()
            if fish["age"] < FISH_LIFETIME
        ]

    def _process_fish(self) -> None:
        """处理鱼：生成新鱼 + 生命周期推进"""
        # ── 生成 ──
        is_night = self._is_night_time()
        spawn_chance = FISH_SPAWN_CHANCE
        if is_night:
            spawn_chance *= FISH_SPAWN_NIGHT_REDUCTION

        pressure_mult = getattr(self._pressure_map, 'get_spawn_multiplier', None)
        season_mult = self._get_season_mult("fish")

        for zone in self._fish_spawn_zones:
            if zone in self._fish:
                continue
            hotspot = self._fish_hotspot.get(zone, 1.0)
            p_mult = pressure_mult(zone[0], zone[1]) if pressure_mult else 1.0
            if random.random() < spawn_chance * hotspot * p_mult * season_mult:
                self._fish[zone] = {"age": 0}
                x, y = zone
                print(f"[ECO] Fish spawned at ({x},{y})")

        # ── 生命周期推进 ──
        expired = []
        for pos, fish in self._fish.items():
            fish["age"] += 1
            if fish["age"] >= FISH_LIFETIME:
                expired.append(pos)
        for pos in expired:
            x, y = pos
            print(f"[ECO] Fish at ({x},{y}) disappeared")
            del self._fish[pos]

    # ══════════════════════════════════════════
    # 人流量系统
    # ══════════════════════════════════════════

    def set_pressure_map(self, pressure_map: object) -> None:
        """注入区域压力图引用（T-019）"""
        self._pressure_map = pressure_map

        # T-031: 从base_fertility初始化current_fertility
        if hasattr(pressure_map, 'base_fertility'):
            for rid, base_val in pressure_map.base_fertility.items():
                self.current_fertility[rid] = base_val

        # T-031: 预计算tile→region映射
        if hasattr(pressure_map, '_tile_to_region_id'):
            for zone in self._mushroom_spawn_zones:
                rid = pressure_map._tile_to_region_id(zone[0], zone[1])
                if rid:
                    self._tile_region_map[zone] = rid

    def set_time_system(self, time_system: object) -> None:
        """注入时间系统引用（T-027 季节）"""
        self._time_system = time_system

    def _get_season_mult(self, resource: str) -> float:
        """返回当前季节对某类资源的倍率"""
        from config import (
            SEASON_FISH_BONUS, SEASON_MUSHROOM_BONUS, SEASON_REGROWTH_BONUS,
        )
        if self._time_system is None:
            return 1.0
        season = self._time_system.get_season()
        bonus_map = {
            "mushroom": SEASON_MUSHROOM_BONUS,
            "fish": SEASON_FISH_BONUS,
            "forest": SEASON_REGROWTH_BONUS,
        }
        return bonus_map.get(resource, {}).get(season, 1.0)

    def record_traffic(self, x: int, y: int) -> None:
        """记录NPC经过某tile（累积+近期）"""
        key = (x, y)
        self._footfall[key] = self._footfall.get(key, 0) + 1
        self._recent_traffic[key] = self._recent_traffic.get(key, 0) + 1

    def _decay_traffic(self) -> None:
        """每帧衰减近期人流量计数（累积脚流量永不衰减）"""
        decayed = []
        for pos, count in self._recent_traffic.items():
            new_count = count * TRAFFIC_DECAY
            if new_count < 0.01:
                decayed.append(pos)
            else:
                self._recent_traffic[pos] = new_count
        for pos in decayed:
            del self._recent_traffic[pos]

    def get_traffic(self, x: int, y: int) -> int:
        """返回指定坐标的人流量（累积脚流量）"""
        return self._footfall.get((x, y), 0)

    def get_recent_traffic(self, x: int, y: int) -> float:
        """返回近期人流量（可衰减）"""
        return self._recent_traffic.get((x, y), 0.0)

    # ══════════════════════════════════════════
    # NPC觅食查询
    # ══════════════════════════════════════════

    def find_nearest_food(
        self, from_x: int, from_y: int
    ) -> Optional[tuple[int, int, str]]:
        """寻找最近的食物源（森林食物/蘑菇/鱼）。
        返回 (x, y, type) 其中type为"forest"/"mushroom"/"fish"。
        无可用食物返回None。
        """
        best_dist = float("inf")
        best: Optional[tuple[int, int, str]] = None

        # 1. 检查森林食物
        for fx, fy in self.available_forests():
            dist = (fx - from_x) ** 2 + (fy - from_y) ** 2
            if dist < best_dist:
                best_dist = dist
                best = (fx, fy, "forest")

        # 2. 检查蘑菇
        for mx, my, _stage in self.available_mushrooms():
            dist = (mx - from_x) ** 2 + (my - from_y) ** 2
            if dist < best_dist:
                best_dist = dist
                best = (mx, my, "mushroom")

        # 3. 检查鱼
        for fx, fy in self.available_fish():
            dist = (fx - from_x) ** 2 + (fy - from_y) ** 2
            if dist < best_dist:
                best_dist = dist
                best = (fx, fy, "fish")

        return best

    def collect_food_at(self, x: int, y: int, food_type: str) -> int:
        """在指定坐标采集指定类型的食物。
        返回实际获得的营养值（减少的饥饿值）。
        """
        if food_type == "forest":
            return self.collect(x, y) * 30  # 1单位食物 = 30饥饿
        elif food_type == "mushroom":
            return self.collect_mushroom(x, y)
        elif food_type == "fish":
            return self.collect_fish(x, y)
        return 0

    # ══════════════════════════════════════════
    # 生态主更新
    # ══════════════════════════════════════════

    def _is_night_time(self) -> bool:
        """粗略判断是否夜晚（基于生态帧计数）"""
        # 生态帧计数因5NPC去重，实际约240帧一个完整昼夜(≈4s@60fps)
        phase = self._eco_call_count % 1200
        return 400 <= phase < 1000  # 大约1/3时间夜晚

    def update(self) -> None:
        """生态主更新。会被NPC多次调用但只处理一次。"""
        self._eco_call_count += 1
        # 5个NPC每帧各调用一次，每5次才实际处理一次
        if self._eco_call_count % 5 != 1:
            return

        self._eco_tick += 1

        # T-031: 重置生育跟踪
        self._spawned_regions = set()

        # 每60生态帧(~5秒)更新一次热点漂移
        if self._eco_tick % 60 == 0:
            self._update_hotspot_drift()

        self._process_regrowth()
        self._process_mushrooms()
        self._process_fish()
        self._decay_traffic()

        # T-031: fertility自然恢复（无再生区域恢复fertility）
        for rid in list(self.current_fertility.keys()):
            if rid not in self._spawned_regions:
                self.current_fertility[rid] += FERTILITY_NATURAL_RECOVERY
            # clamp: [0.0, base_fertility]
            base = 1.0
            pm_base = getattr(self._pressure_map, 'base_fertility', None)
            if pm_base:
                base = pm_base.get(rid, 1.0)
            self.current_fertility[rid] = max(0.0, min(base, self.current_fertility[rid]))

    # ══════════════════════════════════════════
    # 可视化查询（供main.py渲染用，只读访问）
    # ══════════════════════════════════════════

    @property
    def depleted_forests(self) -> set[tuple[int, int]]:
        """depleted森林坐标集合"""
        return self._depleted

    @property
    def mushrooms(self) -> dict[tuple[int, int], dict]:
        """所有蘑菇 {pos: {age, stage_str}}"""
        result = {}
        for pos, mush in self._mushrooms.items():
            result[pos] = {
                "age": mush["age"],
                "stage": self._get_mushroom_stage(mush),
            }
        return result

    @property
    def fish(self) -> dict[tuple[int, int], dict]:
        """所有鱼 {pos: {age}}"""
        result = {}
        for pos, fish in self._fish.items():
            result[pos] = {"age": fish["age"]}
        return result

    # ══════════════════════════════════════════
    # 旧接口兼容
    # ══════════════════════════════════════════

    def resource_count(self, resource_type: str = "food") -> int:
        if resource_type != "food":
            return 0
        return len(self.available_forests())

    def active_resources(self) -> list:
        return [
            _ForestResource(x, y, stock)
            for (x, y), stock in self._food_stock.items()
            if stock > 0
        ]

    def get_resource(self, x: int, y: int):
        if (x, y) in self._food_stock and self._food_stock[(x, y)] > 0:
            return _ForestResource(x, y, self._food_stock[(x, y)])
        return None


class _ForestResource:
    """森林资源简单包装（兼容旧接口、用于测试查询）"""

    def __init__(self, x: int, y: int, amount: int) -> None:
        self.x = x
        self.y = y
        self.resource_type = "food"
        self.amount = amount
        self.collected = False
