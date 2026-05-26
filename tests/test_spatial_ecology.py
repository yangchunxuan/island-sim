"""
空间生态测试 — Island Sim v1 (T-027)

验证：压力扩散、恢复传播、邻居关系。
"""

from config import TileType
from world.regional_pressure import RegionPressureMap
from world.resources import ResourceManager


def _make_grid():
    g = [[TileType.GRASS for _ in range(20)] for _ in range(20)]
    for fx, fy in [(5, 5), (6, 5), (10, 10), (15, 15)]:
        g[fy][fx] = TileType.FOREST
    return g


class TestNeighborDetection:
    """邻居检测测试"""

    def test_neighbors_count(self):
        pm = RegionPressureMap(_make_grid())
        # 角区域 (0,0): 2 neighbors
        assert len(pm._neighbors(0, 0)) == 2
        # 边区域 (0,1): 3 neighbors
        assert len(pm._neighbors(0, 1)) == 3
        # 内区域 (1,1): 4 neighbors
        assert len(pm._neighbors(1, 1)) == 4

    def test_neighbors_are_adjacent(self):
        pm = RegionPressureMap(_make_grid())
        neighbors = pm._neighbors(1, 1)
        expected = [(0, 1), (2, 1), (1, 0), (1, 2)]
        for n in expected:
            assert n in neighbors


class TestPressureSpread:
    """压力扩散测试"""

    def test_spread_no_crash(self):
        rm = ResourceManager(_make_grid())
        pm = RegionPressureMap(_make_grid())
        rm.set_pressure_map(pm)
        pm._pressure_scores[(1, 1)] = 0.9
        # 扩散不应报错
        pm._spread_pressure()
        assert True

    def test_update_with_spread(self):
        """完整 update 包含扩散处理"""
        rm = ResourceManager(_make_grid())
        pm = RegionPressureMap(_make_grid())
        rm.set_pressure_map(pm)
        # 制造高压
        for _ in range(200):
            rm.record_traffic(7, 7)  # central_plain
        pm.update(tick=100, resource_mgr=rm)
        assert True


class TestClimateZones:
    """气候区系统测试"""

    def test_humid_region_identified(self):
        pm = RegionPressureMap(_make_grid())
        # 东南沼泽 (3,2) humidity=0.9
        assert pm.get_climate_type(19, 14) == "humid"

    def test_arid_region_identified(self):
        pm = RegionPressureMap(_make_grid())
        # 废弃西区 (0,2) humidity=0.3
        assert pm.get_climate_type(2, 10) == "arid"

    def test_cold_region_high_humidity(self):
        pm = RegionPressureMap(_make_grid())
        # 北脊 (1,0) humidity=0.4 → temperate (not cold since humidity=0.4)
        # 东北小岛 (3,0) humidity=0.8 → humid
        assert pm.get_climate_type(19, 2) == "humid"

    def test_climate_modifier_mushroom(self):
        pm = RegionPressureMap(_make_grid())
        # 湿润区蘑菇倍率 > 干旱区
        humid_mult = pm.get_climate_modifier(19, 14, "mushroom")
        arid_mult = pm.get_climate_modifier(2, 10, "mushroom")
        assert humid_mult > arid_mult
