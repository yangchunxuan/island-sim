"""
地图模块单元测试 — Island Sim v1

覆盖：地图大小、边界检查、可行走性、建筑物数量、Tile属性、资源系统。
"""

import pytest
from world.map import GameMap
from world.resources import ResourceManager
from config import (
    MAP_WIDTH,
    MAP_HEIGHT,
    TileType,
    TILE_PROPERTIES,
    FOOD_PER_FOREST,
    FOREST_REGROWTH_DAYS,
    DAY_TICKS,
    MUSHROOM_FRESH_DURATION,
    MUSHROOM_OLD_DURATION,
    MUSHROOM_ROTTEN_DURATION,
    FISH_LIFETIME,
)


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
            assert mgr.get_food_amount(x, y) == 0


# ── T-017 生态循环测试 ──


class TestForestRegrowth:
    """森林恢复系统测试"""

    def test_regrowth_starts_on_deplete(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        forests = mgr.available_forests()
        assert len(forests) > 0
        x, y = forests[0]
        for _ in range(FOOD_PER_FOREST):
            mgr.collect(x, y)
        assert mgr.is_depleted(x, y)
        assert (x, y) in mgr._regrowth_timer
        assert mgr._regrowth_timer[(x, y)] > 0

    def test_no_instant_regrowth(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        forests = mgr.available_forests()
        x, y = forests[0]
        for _ in range(FOOD_PER_FOREST):
            mgr.collect(x, y)
        for _ in range(1000):
            mgr.update()
        assert mgr.is_depleted(x, y)

    def test_regrowth_after_time(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        forests = mgr.available_forests()
        x, y = forests[0]
        for _ in range(FOOD_PER_FOREST):
            mgr.collect(x, y)
        total = FOREST_REGROWTH_DAYS * DAY_TICKS + 10
        for _ in range(total * 5):
            mgr.update()
        assert not mgr.is_depleted(x, y)
        assert mgr.get_food_amount(x, y) == FOOD_PER_FOREST

    def test_high_footfall_delays_regrowth_once(self) -> None:
        """高脚流量延迟恢复一次，不会永久阻塞"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        forests = mgr.available_forests()
        x, y = forests[0]
        for _ in range(FOOD_PER_FOREST):
            mgr.collect(x, y)
        assert mgr.is_depleted(x, y)
        assert (x, y) in mgr._regrowth_timer
        original_timer = mgr._regrowth_timer[(x, y)]
        # 制造高脚流量
        for _ in range(100):
            mgr.record_traffic(x, y)
        # 强制让计时器到期
        mgr._regrowth_timer[(x, y)] = 1
        # 跑几帧触发处理
        for _ in range(10):
            mgr.update()
        # 应延迟（timer被重置，不在regrowth_delayed中）
        assert mgr.is_depleted(x, y), "高脚流量应立即延长恢复"
        assert (x, y) in mgr._regrowth_delayed
        # 再次强制让计时器到期
        mgr._regrowth_timer[(x, y)] = 1
        for _ in range(10):
            mgr.update()
        # 延迟过一次后不应再延迟
        assert not mgr.is_depleted(x, y), "延迟一次后应能恢复"

class TestMushroomSystem:
    """蘑菇系统测试"""

    def test_spawn_zones_exist(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        assert len(mgr._mushroom_spawn_zones) > 0

    def test_mushroom_lifecycle(self) -> None:
        """直接用age推断阶段而非循环调用update"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        pos = (10, 10)
        # fresh阶段
        mgr._mushrooms[pos] = {"age": 20}
        assert mgr.is_edible_mushroom(10, 10)
        assert mgr._get_mushroom_stage(mgr._mushrooms[pos]) == "fresh"
        # old阶段
        mgr._mushrooms[pos] = {"age": MUSHROOM_FRESH_DURATION + 20}
        assert mgr.is_edible_mushroom(10, 10)
        assert mgr._get_mushroom_stage(mgr._mushrooms[pos]) == "old"
        # rotten阶段
        mgr._mushrooms[pos] = {"age": MUSHROOM_FRESH_DURATION + MUSHROOM_OLD_DURATION + 10}
        assert not mgr.is_edible_mushroom(10, 10)
        assert mgr._get_mushroom_stage(mgr._mushrooms[pos]) == "rotten"
        # gone阶段
        total = MUSHROOM_FRESH_DURATION + MUSHROOM_OLD_DURATION + MUSHROOM_ROTTEN_DURATION + 20
        mgr._mushrooms[pos] = {"age": total}
        assert mgr._get_mushroom_stage(mgr._mushrooms[pos]) == "gone"

    def test_fresh_mushroom_nutrition(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        mgr._mushrooms[(5, 5)] = {"age": 20}  # fresh阶段（age>=10）
        from config import MUSHROOM_NUTRITION_FRESH
        assert mgr.collect_mushroom(5, 5) == MUSHROOM_NUTRITION_FRESH
        assert (5, 5) not in mgr._mushrooms

    def test_old_mushroom_nutrition(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        mgr._mushrooms[(5, 5)] = {"age": MUSHROOM_FRESH_DURATION + 20}
        from config import MUSHROOM_NUTRITION_OLD
        assert mgr.collect_mushroom(5, 5) == MUSHROOM_NUTRITION_OLD

    def test_rotten_mushroom_inedible(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        total = MUSHROOM_FRESH_DURATION + MUSHROOM_OLD_DURATION + 10
        mgr._mushrooms[(5, 5)] = {"age": total}
        assert not mgr.is_edible_mushroom(5, 5)
        assert mgr.collect_mushroom(5, 5) == 0

    def test_mushroom_update_removes_expired(self) -> None:
        """update()应移除已消失的蘑菇"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        pos = (10, 10)
        total = MUSHROOM_FRESH_DURATION + MUSHROOM_OLD_DURATION + MUSHROOM_ROTTEN_DURATION + 20
        mgr._mushrooms[pos] = {"age": total}
        # 运行5次update确保去重通过后能处理一次
        for _ in range(10):
            mgr.update()
        assert pos not in mgr._mushrooms


class TestFishSystem:
    """鱼类系统测试"""

    def test_fish_spawn_zones_exist(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        assert len(mgr._fish_spawn_zones) > 0

    def test_fish_lifetime(self) -> None:
        """直接用age判断生命周期，而非循环调用update"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        mgr._fish[(5, 5)] = {"age": 0}
        assert mgr.is_edible_fish(5, 5)
        # 直接设置age超过生命周期
        mgr._fish[(5, 5)] = {"age": FISH_LIFETIME + 10}
        assert not mgr.is_edible_fish(5, 5)
        # 运行update检查是否被移除
        for _ in range(10):
            mgr.update()
        assert (5, 5) not in mgr._fish

    def test_fish_collect(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        mgr._fish[(5, 5)] = {"age": 0}
        from config import FISH_NUTRITION
        assert mgr.collect_fish(5, 5) == FISH_NUTRITION
        assert (5, 5) not in mgr._fish
        assert mgr.collect_fish(5, 5) == 0


class TestResourceHotspots:
    """资源热点测试"""

    def test_mushroom_hotspots_exist(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        assert len(mgr._mushroom_hotspot) > 0
        rates = list(mgr._mushroom_hotspot.values())
        assert max(rates) > min(rates) + 0.1

    def test_fish_hotspots_exist(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        assert len(mgr._fish_hotspot) > 0
        rates = list(mgr._fish_hotspot.values())
        assert max(rates) > min(rates) + 0.1

    def test_find_nearest_food_forest(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        result = mgr.find_nearest_food(10, 10)
        assert result is not None
        assert result[2] == "forest"

    def test_find_nearest_food_none(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        for (fx, fy) in list(mgr.available_forests()):
            for _ in range(FOOD_PER_FOREST):
                mgr.collect(fx, fy)
        result = mgr.find_nearest_food(10, 10)
        assert result is None


class TestTrafficSystem:
    """人流量追踪测试"""

    def test_traffic_records(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        mgr.record_traffic(5, 5)
        assert mgr.get_traffic(5, 5) > 0

    def test_recent_traffic_decays(self) -> None:
        """近期人流量随时间衰减"""
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        mgr.record_traffic(5, 5)
        mgr.record_traffic(5, 5)
        initial = mgr.get_recent_traffic(5, 5)
        for _ in range(100):
            mgr.update()
        assert mgr.get_recent_traffic(5, 5) < initial

    def test_no_traffic_unvisited(self) -> None:
        game_map = GameMap()
        mgr = ResourceManager(game_map._grid)
        assert mgr.get_traffic(0, 0) == 0
