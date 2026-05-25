"""
区域压力地图 — Island Sim v1

T-019: 将地图分为4x4区域(5x5tile)，追踪生态压力，影响资源生成。
"""

from config import MAP_HEIGHT, MAP_WIDTH, REGION_SIZE, TileType


class RegionPressureMap:
    """区域压力图：追踪和计算地图各区域的生态压力"""

    REGION_COLS: int = MAP_WIDTH // REGION_SIZE   # 4
    REGION_ROWS: int = MAP_HEIGHT // REGION_SIZE  # 4

    def __init__(self, grid: list[list[TileType]]) -> None:
        self._grid = grid
        self._pressure_scores: dict[tuple[int, int], float] = {}
        self._collapsed: set[tuple[int, int]] = set()
        self._last_collapse_tick: dict[tuple[int, int], int] = {}

    # ── 坐标工具 ──

    @staticmethod
    def tile_to_region(tx: int, ty: int) -> tuple[int, int]:
        """tile坐标 → 区域坐标"""
        return (tx // REGION_SIZE, ty // REGION_SIZE)

    def region_name(self, rx: int, ry: int) -> str:
        """区域可读名称"""
        return f"({rx},{ry})"

    # ── 压力计算 ──

    def update(self, tick: int, resource_mgr: object) -> list[tuple[str, tuple[int, int]]]:
        """更新所有区域压力值，返回新发生的崩溃/恢复事件"""
        events: list[tuple[str, tuple[int, int]]] = []
        for ry in range(self.REGION_ROWS):
            for rx in range(self.REGION_COLS):
                r = (rx, ry)
                score = self._calc_score(rx, ry, resource_mgr)
                self._pressure_scores[r] = score

                if score > 0.8 and r not in self._collapsed:
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
        return min(1.0, activity * 0.5 + depletion * 0.5)

    # ── 对资源的影响 ──

    def get_spawn_multiplier(self, tx: int, ty: int) -> float:
        """压力对资源生成率的倍率影响"""
        score = self.get_score(tx, ty)
        if score > 0.6:
            return 0.5
        if score < 0.2:
            return 1.5
        return 1.0

    def get_regrowth_multiplier(self, tx: int, ty: int) -> float:
        """压力对森林恢复速度的倍率影响"""
        score = self.get_score(tx, ty)
        if score > 0.6:
            return 0.75
        if score < 0.2:
            return 1.25
        return 1.0

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

    @property
    def collapsed_regions(self) -> set[tuple[int, int]]:
        return self._collapsed
