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
        # nw_forest humidity=0.6 → base_fertility=0.6
        nw = pm.get_fertility_by_region(0, 0)
        # abandoned_west humidity=0.3 → base_fertility=0.3
        ab = pm.get_fertility_by_region(0, 2)
        assert nw > ab

    def test_refugia_identification(self):
        pm = RegionPressureMap(_make_grid())
        refugia = pm.get_refugia_list()
        assert len(refugia) >= 2
        # ne_coast humidity=0.7 → base_fertility=0.9 ≥ REFUGIA_THRESHOLD(0.65)
        assert "东北海岸" in refugia

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
        high = pm.get_spawn_multiplier(2, 2)     # nw_forest fert=0.6
        low = pm.get_spawn_multiplier(2, 17)     # sw_rocks fert=0.3
        assert high > low

    def test_fertility_affects_regrowth(self):
        """高 fertility 区域恢复倍率更高"""
        pm = RegionPressureMap(_make_grid())
        high = pm.get_regrowth_multiplier(2, 2)  # nw_forest
        low = pm.get_regrowth_multiplier(2, 17)  # sw_rocks
        assert high > low


class TestBaseFertility:
    """静态 base_fertility 测试（FR-001 Stage 2a）"""

    def test_all_regions_have_base_fertility(self):
        pm = RegionPressureMap(_make_grid())
        assert len(pm.base_fertility) == 16  # 4×4 = 16 个区域
        for rid, fert in pm.base_fertility.items():
            assert fert > 0.0, f"{rid} 的 base_fertility 为 0"

    def test_base_fertility_in_range(self):
        pm = RegionPressureMap(_make_grid())
        for fert in pm.base_fertility.values():
            assert 0.0 <= fert <= 1.0, f"base_fertility {fert} 超出 [0.0, 1.0]"

    def test_base_fertility_via_getter(self):
        pm = RegionPressureMap(_make_grid())
        # 按区域名称访问
        assert pm.get_base_fertility("东北海岸") == 0.9   # humidity=0.7
        assert pm.get_base_fertility("中央平原") == 0.6   # 0.35<humidity=0.5<0.7
        assert pm.get_base_fertility("废弃西区") == 0.3   # humidity=0.3≤0.35

    def test_base_fertility_by_id(self):
        pm = RegionPressureMap(_make_grid())
        assert pm.get_base_fertility("ne_coast") == 0.9
        assert pm.get_base_fertility("central_plain") == 0.6

    def test_fertility_hierarchy(self):
        """高湿度区域 > 中湿度区域 > 低湿度区域（对应森林>草地>沙地）"""
        pm = RegionPressureMap(_make_grid())
        # 高湿度带（humidity>=0.7 → 0.9）：类似森林
        high = pm.get_base_fertility("东北海岸")
        # 中湿度带（0.35<humidity<0.7 → 0.6）：类似草地
        mid = pm.get_base_fertility("中央平原")
        # 低湿度带（humidity<=0.35 → 0.3）：类似沙地
        low = pm.get_base_fertility("废弃西区")
        assert high > mid > low, f"{high} > {mid} > {low} 应当成立"

    def test_base_fertility_immutable(self):
        """base_fertility 没有 setter，不能通过赋值修改"""
        pm = RegionPressureMap(_make_grid())
        rid = list(pm.base_fertility.keys())[0]
        original = pm.base_fertility[rid]
        # 通过 getter 验证值未变
        assert pm.get_base_fertility(rid) == original
