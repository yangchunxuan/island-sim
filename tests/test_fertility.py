"""
地力系统测试 — Island Sim v1 (T-027)

验证：fertility 变化、对资源生成影响、避难所识别。
"""

from config import TileType
from world.regional_pressure import RegionPressureMap
from world.resources import ResourceManager


def _make_grid():
    g = [[TileType.GRASS for _ in range(20)] for _ in range(20)]
    for fx, fy in [(5, 5), (6, 5), (10, 10), (15, 15)]:
        g[fy][fx] = TileType.FOREST
    return g


class TestFertilityBasics:
    """fertility 基本功能测试"""

    def test_initial_values(self):
        pm = RegionPressureMap(_make_grid())
        fert = pm.get_fertility(2, 2)
        assert 0.0 < fert <= 1.0

    def test_region_differences(self):
        pm = RegionPressureMap(_make_grid())
        # 西北森林 fert=0.8
        nw = pm.get_fertility_by_region(0, 0)
        # 废弃西区 fert=0.2
        ab = pm.get_fertility_by_region(0, 2)
        assert nw > ab

    def test_refugia_identification(self):
        pm = RegionPressureMap(_make_grid())
        refugia = pm.get_refugia_list()
        assert len(refugia) >= 2
        assert "西北森林" in refugia

    def test_climate_integration(self):
        pm = RegionPressureMap(_make_grid())
        # se_marsh (grid 3,2) humidity=0.9 → humid
        climate = pm.get_climate_type(19, 14)
        assert climate == "humid"
        # 废弃西区 (grid 0,2) humidity=0.3 → arid
        climate = pm.get_climate_type(2, 12)
        assert climate == "arid"


class TestFertilityImpact:
    """fertility 对资源的影响测试"""

    def test_fertility_affects_spawn(self):
        """高 fertility 区域生成倍率更高"""
        pm = RegionPressureMap(_make_grid())
        high = pm.get_spawn_multiplier(2, 2)     # nw_forest fert=0.8
        low = pm.get_spawn_multiplier(2, 17)     # sw_rocks fert=0.2
        assert high > low

    def test_fertility_affects_regrowth(self):
        """高 fertility 区域恢复倍率更高"""
        pm = RegionPressureMap(_make_grid())
        high = pm.get_regrowth_multiplier(2, 2)  # nw_forest
        low = pm.get_regrowth_multiplier(2, 17)  # sw_rocks
        assert high > low
