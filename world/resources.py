"""
资源管理模块 — 孤岛资源点采集与刷新

提供ResourceManager类，管理地图上的可采集资源（如FOREST中的食物）。
"""

import random
from config import TileType, TILE_PROPERTIES


class Resource:
    """单个资源点"""

    def __init__(self, x: int, y: int, resource_type: str, amount: int = 1) -> None:
        self.x = x
        self.y = y
        self.resource_type = resource_type
        self.amount = amount
        self.collected: bool = False
        self.timer: int = 0  # 刷新倒计时（tick数）


class ResourceManager:
    """管理地图上所有可采集资源点"""

    def __init__(
        self, grid: list[list[TileType]], refresh_ticks: int = 600
    ) -> None:
        self._resources: dict[tuple[int, int], Resource] = {}
        self._refresh_ticks = refresh_ticks
        self._spawn_on_grid(grid)

    # ── 生成 ──

    def _spawn_on_grid(self, grid: list[list[TileType]]) -> None:
        """在可产出资源的tile上（resource_type不为None）按概率生成资源"""
        for y in range(len(grid)):
            for x in range(len(grid[y])):
                tile = grid[y][x]
                props = TILE_PROPERTIES.get(tile, {})
                rtype = props.get("resource_type")
                if rtype is not None:
                    if random.random() < 0.6:
                        amount = random.randint(1, 3)
                        self._resources[(x, y)] = Resource(x, y, str(rtype), amount)

    # ── 查询 ──

    def get_resource(self, x: int, y: int) -> Resource | None:
        """返回指定坐标的未采集资源，没有则返回None"""
        res = self._resources.get((x, y))
        if res is not None and not res.collected:
            return res
        return None

    def active_resources(self) -> list[Resource]:
        """返回所有当前可采集的资源点"""
        return [r for r in self._resources.values() if not r.collected]

    def resource_count(self, resource_type: str = "food") -> int:
        """返回指定类型的有效资源点数量"""
        return sum(
            1
            for r in self._resources.values()
            if not r.collected and r.resource_type == resource_type
        )

    # ── 采集 ──

    def collect(self, x: int, y: int) -> int:
        """采集资源，返回获得的数量（采集后进入冷却倒计时）"""
        res = self.get_resource(x, y)
        if res is None:
            return 0
        amount = res.amount
        res.collected = True
        res.amount = 0
        res.timer = self._refresh_ticks
        return amount

    # ── 刷新 ──

    def update(self) -> None:
        """每帧调用：递减计时器，到期资源重生"""
        for res in self._resources.values():
            if res.collected:
                res.timer -= 1
                if res.timer <= 0:
                    res.collected = False
                    res.amount = random.randint(1, 3)
                    res.timer = 0
