"""
地图模块单元测试 — Island Sim v1

覆盖：地图大小、边界检查、可行走性、建筑物数量、Tile属性、资源系统。
"""

import pytest
from world.map import GameMap
from world.resources import ResourceManager
from config import MAP_WIDTH, MAP_HEIGHT, TileType, TILE_PROPERTIES


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


class TestTileProperties:
    """TILE_PROPERTIES配置正确性测试"""

    def test_all_types_have_properties(self) -> None:
        """每个TileType都有对应的属性配置"""
        for tile_type in TileType:
            assert tile_type in TILE_PROPERTIES, f"{tile_type}缺少属性配置"

    def test_water_walkable_false(self) -> None:
        assert TILE_PROPERTIES[TileType.WATER]["walkable"] is False

    def test_rock_walkable_false(self) -> None:
        assert TILE_PROPERTIES[TileType.ROCK]["walkable"] is False

    def test_grass_walkable_true(self) -> None:
        assert TILE_PROPERTIES[TileType.GRASS]["walkable"] is True

    def test_forest_resource_type_food(self) -> None:
        assert TILE_PROPERTIES[TileType.FOREST]["resource_type"] == "food"

    def test_house_can_sleep_true(self) -> None:
        assert TILE_PROPERTIES[TileType.HOUSE]["can_sleep"] is True

    def test_campfire_can_socialize_true(self) -> None:
        assert TILE_PROPERTIES[TileType.CAMPFIRE]["can_socialize"] is True

    def test_is_walkable_consistent_with_properties(self) -> None:
        """is_walkable()返回值和TILE_PROPERTIES walkable一致"""
        game_map = GameMap()
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                tile = game_map.get_tile(x, y)
                expected = TILE_PROPERTIES[tile]["walkable"]
                assert game_map.is_walkable(x, y) == expected, (
                    f"({x},{y}) tile={tile}: is_walkable与属性不一致"
                )


class TestResourceManager:
    """ResourceManager有限食物资源测试"""

    def test_resources_spawn_on_forest(self) -> None:
        """每个FOREST tile应分配初始食物储量"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        count = mgr.forest_count()
        assert count > 0, "地图上应有FOREST tile"
        assert mgr.total_food_remaining() == count * 3, (
            f"每个森林应有3食物，共{count}个森林，总量应为{count*3}"
        )

    def test_all_forests_have_food_amount(self) -> None:
        """每个FOREST tile的food_amount应为FOOD_PER_FOREST"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        for y in range(len(game_map._grid)):
            for x in range(len(game_map._grid[y])):
                if game_map._grid[y][x] == TileType.FOREST:
                    assert mgr.get_food_amount(x, y) == 3, (
                        f"FOREST ({x},{y}) 应有3食物"
                    )

    def test_no_resource_on_non_resource_tiles(self) -> None:
        """非FOREST tile上不应有食物储量"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        for y in range(len(game_map._grid)):
            for x in range(len(game_map._grid[y])):
                if game_map._grid[y][x] != TileType.FOREST:
                    assert mgr.get_food_amount(x, y) == 0, (
                        f"({x},{y}) {game_map._grid[y][x]}不应有食物"
                    )

    def test_collect_returns_one(self) -> None:
        """采集有食物的森林返回1"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        forests = mgr.available_forests()
        if forests:
            x, y = forests[0]
            amount = mgr.collect(x, y)
            assert amount == 1

    def test_collect_decrements_food(self) -> None:
        """采集后森林食物量减少"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        forests = mgr.available_forests()
        if forests:
            x, y = forests[0]
            before = mgr.get_food_amount(x, y)
            mgr.collect(x, y)
            assert mgr.get_food_amount(x, y) == before - 1

    def test_depleted_forest_returns_zero(self) -> None:
        """耗尽后的森林采集返回0"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        forests = mgr.available_forests()
        if forests:
            x, y = forests[0]
            # 采光所有食物
            for _ in range(3):
                mgr.collect(x, y)
            assert mgr.is_depleted(x, y)
            assert mgr.collect(x, y) == 0

    def test_depleted_forest_not_in_available(self) -> None:
        """耗尽后的森林不出现在available_forests中"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        forests = mgr.available_forests()
        if forests:
            x, y = forests[0]
            for _ in range(3):
                mgr.collect(x, y)
            assert (x, y) not in mgr.available_forests()

    def test_collect_empty_tile_returns_zero(self) -> None:
        """采集无效坐标返回0"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        assert mgr.collect(-1, -1) == 0

    def test_no_resource_regeneration(self) -> None:
        """耗尽后的森林即使update也不会重生食物"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        forests = mgr.available_forests()
        if forests:
            x, y = forests[0]
            for _ in range(3):
                mgr.collect(x, y)
            assert mgr.is_depleted(x, y)
            # 运行大量update也不应重生
            for _ in range(2000):
                mgr.update()
            assert mgr.is_depleted(x, y)
            assert mgr.get_food_amount(x, y) == 0
