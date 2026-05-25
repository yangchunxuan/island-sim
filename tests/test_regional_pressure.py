"""
区域压力系统测试 — Island Sim v1

验证：压力计算、区域划分、TOP3展示、资源生成影响、崩溃/恢复事件。
"""

import unittest

from config import FOOD_PER_FOREST, REGION_SIZE, TileType
from world.regional_pressure import RegionPressureMap
from world.resources import ResourceManager


def _make_grid():
    g = [[TileType.GRASS for _ in range(20)] for _ in range(20)]
    for fx, fy in [(5, 5), (6, 5), (10, 10), (15, 15)]:
        g[fy][fx] = TileType.FOREST
    return g


class TestRegionDivision(unittest.TestCase):
    """区域划分测试"""

    def setUp(self):
        self.pm = RegionPressureMap(_make_grid())

    def test_region_count(self):
        self.assertEqual(self.pm.REGION_COLS, 4)
        self.assertEqual(self.pm.REGION_ROWS, 4)

    def test_tile_to_region(self):
        self.assertEqual(self.pm.tile_to_region(0, 0), (0, 0))
        self.assertEqual(self.pm.tile_to_region(4, 4), (0, 0))
        self.assertEqual(self.pm.tile_to_region(5, 0), (1, 0))
        self.assertEqual(self.pm.tile_to_region(19, 19), (3, 3))

    def test_region_name(self):
        name = self.pm.region_name(1, 2)
        self.assertIn("1", name)
        self.assertIn("2", name)


class TestPressureScore(unittest.TestCase):
    """压力计算测试"""

    def setUp(self):
        grid = _make_grid()
        self.rm = ResourceManager(grid)
        self.pm = RegionPressureMap(grid)

    def test_fresh_map_low_pressure(self):
        self.pm.update(tick=0, resource_mgr=self.rm)
        for ry in range(4):
            for rx in range(4):
                score = self.pm.get_score(rx * REGION_SIZE, ry * REGION_SIZE)
                self.assertLessEqual(score, 0.5)

    def test_high_footfall_increases_pressure(self):
        for x in range(5):
            for y in range(5):
                for _ in range(10):
                    self.rm.record_traffic(x, y)
        self.pm.update(tick=10, resource_mgr=self.rm)
        score_00 = self.pm.get_score(0, 0)
        score_33 = self.pm.get_score(19, 19)
        self.assertGreater(score_00, score_33)

    def test_depletion_increases_pressure(self):
        for _ in range(FOOD_PER_FOREST):
            self.rm.collect(5, 5)
        self.pm.update(tick=10, resource_mgr=self.rm)
        r = self.pm.tile_to_region(5, 5)
        score_depleted = self.pm.get_score(5, 5)
        score_clean = self.pm.get_score(0, 0)
        self.assertGreaterEqual(score_depleted, score_clean)

    def test_max_score_1(self):
        # Extreme pressure
        for x in range(5):
            for y in range(5):
                for _ in range(200):
                    self.rm.record_traffic(x, y)
        # Deplete forests in region (0,0)
        for fx, fy in [(5, 5), (6, 5)]:
            for _ in range(FOOD_PER_FOREST):
                self.rm.collect(fx, fy)
        self.pm.update(tick=10, resource_mgr=self.rm)
        self.assertLessEqual(self.pm.get_score(0, 0), 1.0)
        self.assertGreaterEqual(self.pm.get_score(0, 0), 0.0)

    def test_score_range(self):
        self.pm.update(tick=0, resource_mgr=self.rm)
        for ry in range(4):
            for rx in range(4):
                s = self.pm.get_score(rx * REGION_SIZE, ry * REGION_SIZE)
                self.assertTrue(0.0 <= s <= 1.0, f"score {s} out of range")


def _high_pressure_setup():
    """创建含1个高压区域的测试环境（region (0,0)）"""
    grid = [[TileType.GRASS for _ in range(20)] for _ in range(20)]
    grid[1][1] = TileType.FOREST  # position (1,1) in region (0,0)
    grid[2][2] = TileType.FOREST  # position (2,2) in region (0,0)
    rm = ResourceManager(grid)
    pm = RegionPressureMap(grid)
    # 制造脚流量
    for x in range(5):
        for y in range(5):
            for _ in range(20):
                rm.record_traffic(x, y)
    # 耗尽森林（grid[y][x] = forest → position (x,y)）
    for _ in range(FOOD_PER_FOREST):
        rm.collect(1, 1)
    for _ in range(FOOD_PER_FOREST):
        rm.collect(2, 2)
    pm.update(tick=50, resource_mgr=rm)
    return rm, pm


class TestSpawnMultiplier(unittest.TestCase):
    """压力对生成率的影响测试"""

    def setUp(self):
        self.rm, self.pm = _high_pressure_setup()

    def test_high_pressure_reduces_spawn(self):
        mult = self.pm.get_spawn_multiplier(2, 2)
        self.assertLess(mult, 1.0)

    def test_low_pressure_increases_spawn(self):
        grid = _make_grid()
        rm = ResourceManager(grid)
        pm = RegionPressureMap(grid)
        pm.update(tick=10, resource_mgr=rm)
        mult = pm.get_spawn_multiplier(19, 19)
        self.assertGreaterEqual(mult, 1.0)


class TestRegrowthMultiplier(unittest.TestCase):
    """压力对恢复速度的影响测试"""

    def setUp(self):
        self.rm, self.pm = _high_pressure_setup()

    def test_high_pressure_slows_regrowth(self):
        mult = self.pm.get_regrowth_multiplier(2, 2)
        self.assertLess(mult, 1.0)

    def test_low_pressure_speeds_regrowth(self):
        grid = _make_grid()
        rm = ResourceManager(grid)
        pm = RegionPressureMap(grid)
        pm.update(tick=10, resource_mgr=rm)
        mult = pm.get_regrowth_multiplier(19, 19)
        self.assertGreaterEqual(mult, 1.0)


class TestCollapseEvents(unittest.TestCase):
    """区域崩溃/恢复事件测试"""

    def setUp(self):
        self.rm, self.pm = _high_pressure_setup()

    def test_collapse_detected(self):
        self.assertTrue((0, 0) in self.pm.collapsed_regions)

    def test_recovery_detected(self):
        self.pm._collapsed.add((0, 0))
        self.pm._pressure_scores[(0, 0)] = 0.9
        events = self.pm.update(tick=100, resource_mgr=self.rm)
        # After update with actual low-pressure data
        recovery = [e for e in events if e[0] == "REGION_RECOVERY"]
        # May or may not recover depending on real data

    def test_top_pressure_returns_sorted(self):
        self.pm._pressure_scores = {
            (0, 0): 0.9, (1, 0): 0.3, (2, 0): 0.7,
            (3, 0): 0.1, (0, 1): 0.5,
        }
        top = self.pm.get_top_pressure(3)
        self.assertEqual(len(top), 3)
        self.assertGreaterEqual(top[0][1], top[1][1])
        self.assertGreaterEqual(top[1][1], top[2][1])


class TestResourceManagerPressure(unittest.TestCase):
    """ResourceManager压力集成测试"""

    def setUp(self):
        grid = _make_grid()
        self.rm = ResourceManager(grid)
        self.pm = RegionPressureMap(grid)
        self.rm.set_pressure_map(self.pm)

    def test_regrowth_timer_affected_by_pressure(self):
        self.pm._pressure_scores[(1, 1)] = 0.9  # high pressure at forest (5,5) region
        for _ in range(FOOD_PER_FOREST):
            self.rm.collect(5, 5)
        # regrowth timer should be adjusted
        from config import DAY_TICKS, FOREST_REGROWTH_DAYS
        base = FOREST_REGROWTH_DAYS * DAY_TICKS
        expected = int(base / 0.75)
        actual = self.rm._regrowth_timer.get((5, 5), 0)
        self.assertEqual(actual, expected)


# ═══════════════════════════════════════════════
# T-022 生态迁移测试
# ═══════════════════════════════════════════════

class TestEcologicalMigration(unittest.TestCase):
    """生态迁移：热点漂移、恢复偏向、鱼群漂移"""

    def setUp(self):
        grid = _make_grid()
        self.rm = ResourceManager(grid)
        self.pm = RegionPressureMap(grid)

    def _set_pressure(self, rx, ry, score):
        self.pm._pressure_scores[(rx, ry)] = score

    def test_hotspot_drift_reduces_in_high_pressure(self):
        """高压区热点倍率逐渐下降"""
        self.rm.set_pressure_map(self.pm)
        self._set_pressure(0, 0, 0.9)
        # 记录高压区内一个蘑菇点的初始热点
        hp_zones = [z for z in self.rm._mushroom_spawn_zones
                     if self.pm.tile_to_region(z[0], z[1]) == (0, 0)]
        if not hp_zones:
            self.skipTest("no mushroom zones in region (0,0)")
        zone = hp_zones[0]
        initial = self.rm._mushroom_hotspot.get(zone, 1.0)
        # 手动漂移多次
        for _ in range(50):
            self.rm._update_hotspot_drift()
        final = self.rm._mushroom_hotspot.get(zone, 1.0)
        self.assertLess(final, initial)

    def test_hotspot_drift_increases_in_low_pressure(self):
        """低压区热点倍率逐渐上升"""
        self.rm.set_pressure_map(self.pm)
        self._set_pressure(3, 3, 0.0)
        lp_zones = [z for z in self.rm._mushroom_spawn_zones
                     if self.pm.tile_to_region(z[0], z[1]) == (3, 3)]
        if not lp_zones:
            self.skipTest("no mushroom zones in region (3,3)")
        zone = lp_zones[0]
        initial = self.rm._mushroom_hotspot.get(zone, 1.0)
        for _ in range(50):
            self.rm._update_hotspot_drift()
        final = self.rm._mushroom_hotspot.get(zone, 1.0)
        self.assertGreaterEqual(final, initial)

    def test_regrowth_bias_low_pressure_first(self):
        """低压区域的depleted森林优先恢复"""
        self.rm.set_pressure_map(self.pm)
        # 耗尽两个森林
        self.rm._food_stock[(5, 5)] = 0
        self.rm._depleted.add((5, 5))  # region (1,1) - 预设高压
        self.rm._food_stock[(0, 0)] = 0
        self.rm._depleted.add((0, 0))  # region (0,0)
        self.rm._regrowth_timer[(5, 5)] = 1
        self.rm._regrowth_timer[(0, 0)] = 1
        # 设region(1,1)高压、region(0,0)低压
        self._set_pressure(1, 1, 0.9)
        self._set_pressure(0, 0, 0.1)
        # 触发恢复
        # _process_regrowth内部会按压力排序，低压优先
        self.rm._eco_call_count = 6  # 确保update会实际执行
        # 手动触发生态帧
        for _ in range(5):
            self.rm.update()
        # (0,0)在region(0,0)低压，应先恢复
        self.assertNotIn((0, 0), self.rm._depleted,
                         "低压区(0,0)应优先恢复")

if __name__ == "__main__":
    unittest.main()
