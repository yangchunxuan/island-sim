"""
地图模块单元测试 — Island Sim v1

覆盖：地图大小、边界检查、可行走性、建筑物数量、Tile属性、资源系统。
"""

import pytest
from world.map import GameMap
from world.resources import ResourceManager, Resource
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
    """ResourceManager资源系统测试"""

    def test_resources_spawn_on_forest(self) -> None:
        """资源应在FOREST tile上生成"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        count = mgr.resource_count("food")
        assert count > 0, "FOREST tile上应生成食物资源"

    def test_no_resource_on_non_resource_tiles(self) -> None:
        """非产出型tile上不应有资源"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                tile = game_map.get_tile(x, y)
                if TILE_PROPERTIES[tile]["resource_type"] is None:
                    assert mgr.get_resource(x, y) is None, (
                        f"({x},{y}) {tile}不应有资源"
                    )

    def test_collect_returns_amount(self) -> None:
        """采集资源返回正数"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        resources = mgr.active_resources()
        if resources:
            r = resources[0]
            amount = mgr.collect(r.x, r.y)
            assert amount > 0

    def test_collect_removes_resource(self) -> None:
        """采集后资源点不再active"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        resources = mgr.active_resources()
        if resources:
            r = resources[0]
            mgr.collect(r.x, r.y)
            assert mgr.get_resource(r.x, r.y) is None

    def test_collect_empty_tile_returns_zero(self) -> None:
        """采集无效坐标返回0"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        assert mgr.collect(-1, -1) == 0

    def test_update_refreshes_collected_resource(self) -> None:
        """update()推进计时器后资源应重生"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid, refresh_ticks=10)
        resources = mgr.active_resources()
        if resources:
            r = resources[0]
            mgr.collect(r.x, r.y)
            assert mgr.get_resource(r.x, r.y) is None
            # 推进到刷新
            for _ in range(15):
                mgr.update()
            assert mgr.get_resource(r.x, r.y) is not None, "资源未刷新"
