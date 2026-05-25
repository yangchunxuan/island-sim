"""
资源管理模块 — 有限森林食物资源

每个FOREST tile有固定初始食物储量（FOOD_PER_FOREST）。
采集后减少，归零后永久depleted。
无自动重生机制。
"""

from config import FOOD_PER_FOREST, TileType


class ResourceManager:
    """管理地图上FOREST tile的有限食物资源"""

    def __init__(self, grid: list[list[TileType]]) -> None:
        self._food_stock: dict[tuple[int, int], int] = {}
        self._depleted: set[tuple[int, int]] = set()
        self._init_food(grid)

    # ── 初始化 ──

    def _init_food(self, grid: list[list[TileType]]) -> None:
        """为每个FOREST tile分配初始食物储量"""
        for y in range(len(grid)):
            for x in range(len(grid[y])):
                if grid[y][x] == TileType.FOREST:
                    self._food_stock[(x, y)] = FOOD_PER_FOREST

    # ── 查询 ──

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

    # ── 采集 ──

    def collect(self, x: int, y: int) -> int:
        """采集1单位食物。返回实际获得量（0或1）。

        森林储量归零后标记为depleted并输出世界反馈。
        """
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
        return 1

    # ── 旧接口兼容 ──

    def update(self) -> None:
        """空方法，保持接口兼容（T-015禁用资源重生）"""
        pass

    def resource_count(self, resource_type: str = "food") -> int:
        """返回还有食物的森林数量（兼容旧接口）"""
        if resource_type != "food":
            return 0
        return len(self.available_forests())

    def active_resources(self) -> list:
        """返回还有食物的森林坐标（兼容旧接口，返回简单对象列表）"""
        return [
            _ForestResource(x, y, stock)
            for (x, y), stock in self._food_stock.items()
            if stock > 0
        ]

    def get_resource(self, x: int, y: int):
        """返回森林资源对象（兼容旧接口）"""
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
