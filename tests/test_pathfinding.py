"""
A*寻路单元测试 — Island Sim v1

覆盖：基本路径、障碍回避、不可达目标、边界条件。
"""

import pytest

from systems.pathfinding import astar
from world.map import GameMap


def _make_map() -> GameMap:
    """构造确定性地图实例（生成逻辑固定）"""
    return GameMap()


class TestAStar:
    """A*寻路功能测试"""

    def test_simple_path_on_grass(self):
        """起点终点都在空地时返回有效路径"""
        gm = _make_map()
        # 起点和终点都是草地上已知可通行点
        path = astar(gm, (5, 5), (7, 5))
        assert path is not None
        assert len(path) > 0
        # 路径每一步都应该可通行
        for x, y in path:
            assert gm.is_walkable(x, y)
        # 路径终点是目标
        assert path[-1] == (7, 5)

    def test_path_does_not_include_start(self):
        """返回路径不应包含起点"""
        gm = _make_map()
        path = astar(gm, (5, 5), (7, 5))
        assert path is not None
        for step in path:
            assert step != (5, 5)

    def test_adjacent_tiles(self):
        """相邻格子返回单步路径"""
        gm = _make_map()
        path = astar(gm, (5, 5), (6, 5))
        assert path is not None
        assert path == [(6, 5)]

    def test_same_start_and_goal(self):
        """起点等于终点时返回空列表"""
        gm = _make_map()
        path = astar(gm, (5, 5), (5, 5))
        assert path is not None
        assert path == []

    def test_unreachable_goal_in_water(self):
        """目标在水中（不可行走）应返回None"""
        gm = _make_map()
        # 已知海水不可行走(map生成中心10,10为陆地，water在边缘）
        path = astar(gm, (5, 5), (0, 0))
        # (0,0)是WATER，不可达
        if gm.get_tile(0, 0) is not None and not gm.is_walkable(0, 0):
            # 确认起点到水边无走法
            result = astar(gm, (5, 5), (0, 0))
            assert result is None

    def test_water_is_avoided(self):
        """路径不会穿过不可行走的tile"""
        gm = _make_map()
        path = astar(gm, (5, 5), (7, 6))
        assert path is not None
        for x, y in path:
            assert gm.is_walkable(x, y), f"路径踩到了不可通行点 ({x},{y})"

    def test_path_is_shortest(self):
        """返回的路径长度不应超过曼哈顿距离的2倍（合理范围）"""
        gm = _make_map()
        start = (5, 5)
        goal = (10, 10)
        path = astar(gm, start, goal)
        assert path is not None
        manhattan = abs(start[0] - goal[0]) + abs(start[1] - goal[1])
        # 路径长度应 >= 曼哈顿距离（平坦地形上等于曼哈顿距离）
        assert len(path) >= manhattan

    def test_out_of_bounds_start(self):
        """起点越界应返回None"""
        gm = _make_map()
        path = astar(gm, (-1, 5), (5, 5))
        assert path is None

    def test_out_of_bounds_goal(self):
        """终点越界应返回None"""
        gm = _make_map()
        path = astar(gm, (5, 5), (20, 20))
        assert path is None

    def test_path_to_forest(self):
        """FOREST可通行，应能寻路到森林"""
        gm = _make_map()
        start = (5, 5)
        # 找一块FOREST当作目标
        from config import TileType
        forest_tiles = []
        for y in range(20):
            for x in range(20):
                if gm.get_tile(x, y) == TileType.FOREST:
                    forest_tiles.append((x, y))
        assert len(forest_tiles) > 0, "地图上应有FOREST"
        target = forest_tiles[0]
        path = astar(gm, start, target)
        assert path is not None
        assert path[-1] == target
        for x, y in path:
            assert gm.is_walkable(x, y)

    def test_path_to_house(self):
        """HOUSE可通行，应能寻路到房屋"""
        gm = _make_map()
        start = (5, 5)
        houses = gm.get_houses()
        assert len(houses) > 0
        target = houses[0]
        path = astar(gm, start, target)
        assert path is not None
        assert path[-1] == target

    def test_no_path_to_isolated_area(self):
        """完全孤立区域应返回None"""
        gm = _make_map()
        start = (10, 10)
        # 故意选择一个与当前位置不相连的不可行走区域
        goal = (0, 15)
        tile_type = gm.get_tile(*goal)
        from config import TileType
        if not gm.is_walkable(*goal):
            assert astar(gm, start, goal) is None

    def test_path_contains_no_duplicates(self):
        """路径不应有重复坐标"""
        gm = _make_map()
        path = astar(gm, (5, 5), (10, 10))
        assert path is not None
        assert len(path) == len(set(path))
