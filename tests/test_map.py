"""
地图模块单元测试 — Island Sim v1

覆盖：地图大小、边界检查、可行走性、建筑物数量。
"""

import pytest
from world.map import GameMap
from config import MAP_WIDTH, MAP_HEIGHT, TileType


class TestGameMap:
    """GameMap功能测试"""

    def test_map_size(self) -> None:
        """地图应为20x20网格，所有格子有有效tile"""
        game_map = GameMap()
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                tile = game_map.get_tile(x, y)
                assert tile is not None, f"({x}, {y}) 返回None"

    def test_get_tile_out_of_bounds(self) -> None:
        """越界访问应返回None"""
        game_map = GameMap()
        assert game_map.get_tile(-1, 0) is None
        assert game_map.get_tile(0, -1) is None
        assert game_map.get_tile(MAP_WIDTH, 0) is None
        assert game_map.get_tile(0, MAP_HEIGHT) is None

    def test_is_walkable_water(self) -> None:
        """海水不可行走"""
        game_map = GameMap()
        water_found = False
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if game_map.get_tile(x, y) == TileType.WATER:
                    assert not game_map.is_walkable(x, y)
                    water_found = True
        assert water_found, "地图应包含WATER tile"

    def test_is_walkable_grass(self) -> None:
        """草地可行走"""
        game_map = GameMap()
        grass_found = False
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if game_map.get_tile(x, y) == TileType.GRASS:
                    assert game_map.is_walkable(x, y)
                    grass_found = True
        assert grass_found, "地图应包含GRASS tile"

    def test_is_walkable_rock(self) -> None:
        """岩石不可行走"""
        game_map = GameMap()
        rock_found = False
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if game_map.get_tile(x, y) == TileType.ROCK:
                    assert not game_map.is_walkable(x, y)
                    rock_found = True
        assert rock_found, "地图应包含ROCK tile"

    def test_is_walkable_out_of_bounds(self) -> None:
        """越界坐标不可行走"""
        game_map = GameMap()
        assert not game_map.is_walkable(-1, -1)
        assert not game_map.is_walkable(MAP_WIDTH, MAP_HEIGHT)

    def test_house_count(self) -> None:
        """地图应有5个房屋"""
        game_map = GameMap()
        houses = game_map.get_houses()
        assert len(houses) == 5

    def test_houses_are_valid_positions(self) -> None:
        """所有房屋坐标在有效范围内"""
        game_map = GameMap()
        houses = game_map.get_houses()
        for x, y in houses:
            tile = game_map.get_tile(x, y)
            assert tile == TileType.HOUSE, f"房屋({x},{y})tile类型不对"

    def test_campfire_exists(self) -> None:
        """地图应有1个篝火"""
        game_map = GameMap()
        campfire_count = 0
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if game_map.get_tile(x, y) == TileType.CAMPFIRE:
                    campfire_count += 1
        assert campfire_count == 1
