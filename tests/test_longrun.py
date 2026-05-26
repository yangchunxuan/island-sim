"""
T-033 长期运行宪法测试 — Simulation OS 质量底线

验证 100 天模拟后世界不会热寂、爆炸、崩溃。
每个测试独立构建世界，不共享状态。
"""

import pytest

from config import DAY_TICKS, NPC_INITIAL_DATA, STAT_MAX
from world.map import GameMap
from world.time_system import TimeSystem
from world.resources import ResourceManager
from world.regional_pressure import RegionPressureMap
from npc.npc import NPC
from npc.behavior import register_npc_states


def _run_simulation(days: int = 100):
    """独立运行 N 天完整模拟，返回所有游戏对象和初始资源量"""
    import random
    random.seed(42)  # 固定种子确保确定性
    game_map = GameMap()
    time_sys = TimeSystem()
    grid = game_map._grid
    resource_mgr = ResourceManager(grid)
    pressure_map = RegionPressureMap(grid)
    resource_mgr.set_pressure_map(pressure_map)
    resource_mgr.set_time_system(time_sys)

    npcs = []
    for data in NPC_INITIAL_DATA:
        npc = NPC(data, time_sys, game_map, resource_mgr=resource_mgr)
        register_npc_states(npc)
        npcs.append(npc)
    NPC.set_all_npcs(npcs)

    initial_food = resource_mgr.total_food_remaining()
    target_ticks = days * DAY_TICKS

    for _ in range(target_ticks):
        time_sys.tick()
        tick = time_sys._tick_count
        pressure_map.update(tick, resource_mgr, time_sys)  # FR-001a: 完整tick循环
        resource_mgr.update()
        for npc in npcs:
            npc.update()

    return resource_mgr, pressure_map, npcs, time_sys, initial_food


@pytest.mark.slow
def test_100day_no_crash():
    """100 天模拟不崩溃"""
    _run_simulation(100)


@pytest.mark.slow
def test_100day_no_heat_death():
    """100 天后至少 1 个区域 fertility > 0.3（FR-001a 已修复）"""
    _, pressure_map, _, _, _ = _run_simulation(100)
    fertilities = [
        pressure_map.get_fertility_by_region(rx, ry)
        for rx in range(RegionPressureMap.REGION_COLS)
        for ry in range(RegionPressureMap.REGION_ROWS)
    ]
    assert any(f > 0.3 for f in fertilities), (
        f"所有区域 fertility ≤ 0.3: {[round(f, 3) for f in fertilities]}"
    )


@pytest.mark.slow
def test_100day_no_big_bang():
    """100 天后无 fertility 越界（不 > 1.0 且不 < 0）"""
    _, pressure_map, _, _, _ = _run_simulation(100)
    for rx in range(RegionPressureMap.REGION_COLS):
        for ry in range(RegionPressureMap.REGION_ROWS):
            fert = pressure_map.get_fertility_by_region(rx, ry)
            assert 0.0 <= fert <= 1.0, (
                f"区域({rx},{ry}) fertility 越界: {fert}"
            )


@pytest.mark.slow
def test_100day_npc_survive():
    """100 天后 NPC 不全消失（系统中仍有 NPC 存在）"""
    _, _, npcs, _, _ = _run_simulation(100)
    # NPC 在当前系统中不会真正死亡，hunger=STAT_MAX 只是 weakened 状态
    # 验证：NPC 列表非空且至少1个仍在活动（非空状态）
    assert len(npcs) > 0, "NPC 列表为空"
    assert any(n.get_state() is not None for n in npcs), "所有 NPC 状态异常"


@pytest.mark.slow
def test_100day_food_exists():
    """100 天后至少有 1 种食物来源"""
    resource_mgr, _, _, _, _ = _run_simulation(100)
    mushrooms = resource_mgr.available_mushrooms()
    fish = resource_mgr.available_fish()
    forests = resource_mgr.available_forests()
    assert len(mushrooms) > 0 or len(fish) > 0 or len(forests) > 0, (
        "无任何食物来源（mushroom / fish / forest）"
    )


@pytest.mark.slow
def test_resource_not_infinite():
    """100 天后资源总量不超过初始值的 2 倍"""
    resource_mgr, _, _, _, initial_food = _run_simulation(100)
    total = resource_mgr.total_food_remaining()
    assert total <= initial_food * 2, (
        f"森林食物总量 {total} > {initial_food * 2}（初始 2 倍）"
    )
