"""
T-031 FR-001 Stage 2b: 蘑菇肥力动态 — 测试

验证：
- high/low fertility 对蘑菇再生的影响
- 再生消耗 fertility
- 自然恢复机制
- 边界截断
- 沙地 fertility 禁区
"""

import random
import unittest
from unittest.mock import patch

from config import TileType
from world.resources import (
    FERTILITY_COST_PER_REGEN,
    FERTILITY_NATURAL_RECOVERY,
    FERTILITY_REGEN_THRESHOLD,
    MUSHROOM_FERTILITY_BASE_RATE,
    ResourceManager,
)


class MockPressureMap:
    """模拟区域压力图 — 为 ResourceManager 提供 base_fertility 和 tile→region 转换"""

    def __init__(self, base_fertility: dict[str, float] | None = None):
        self.base_fertility = base_fertility or {"test_region": 0.9}

    def _tile_to_region_id(self, tx: int, ty: int) -> str:
        return "test_region"


def _make_grid() -> list[list[TileType]]:
    """创建小网格：FOREST 旁恰好 1 个 GRASS 作为蘑菇再生区"""
    g = [[TileType.ROCK for _ in range(20)] for _ in range(20)]
    g[2][2] = TileType.FOREST
    g[0][0] = TileType.GRASS    # 距离 FOREST(2,2) dx=2 dy=2，在2格范围内
    return g


class TestMushroomFertility(unittest.TestCase):
    """蘑菇肥力动态核心测试"""

    def setUp(self):
        self.grid = _make_grid()
        self.rm = ResourceManager(self.grid)

    def _setup_fertility(self, base_fert: float = 0.9) -> MockPressureMap:
        pm = MockPressureMap({"test_region": base_fert})
        self.rm.set_pressure_map(pm)
        return pm

    # ── 基础门槛 ──

    def test_high_fertility_allows_regen(self):
        """高肥力区（>0.3）蘑菇可再生"""
        self._setup_fertility(0.9)
        # random=0.0 确保 spawn 概率检查通过
        with patch('random.random', return_value=0.0):
            self.rm._process_mushrooms()
        self.assertGreater(len(self.rm._mushrooms), 0,
                           "高肥力区应能长出蘑菇")

    def test_low_fertility_blocks_regen(self):
        """低肥力区（<=0.3）蘑菇无法再生"""
        self._setup_fertility(0.3)
        with patch('random.random', return_value=0.0):
            self.rm._process_mushrooms()
        self.assertEqual(len(self.rm._mushrooms), 0,
                         "肥力<=0.3 时不长蘑菇")

    # ── 消耗 ──

    def test_regen_costs_fertility(self):
        """每次再生消耗 FERTILITY_COST_PER_REGEN"""
        self._setup_fertility(0.9)
        rid = "test_region"
        before = self.rm.current_fertility[rid]
        with patch('random.random', return_value=0.0):
            self.rm._process_mushrooms()
        after = self.rm.current_fertility[rid]
        self.assertAlmostEqual(before - after, FERTILITY_COST_PER_REGEN,
                               msg=f"再生后 fertility 应减少 {FERTILITY_COST_PER_REGEN}")

    # ── 自然恢复 ──

    def test_natural_recovery(self):
        """无再生时 fertility 自然恢复"""
        self._setup_fertility(0.9)
        rid = "test_region"
        # 设到 base 以下，避免 clamp 掩盖恢复效果
        self.rm.current_fertility[rid] = 0.5
        before = self.rm.current_fertility[rid]

        # random=1.0 → 再生概率 0（任何正概率 < 1.0 都不成立）
        with patch('random.random', return_value=1.0):
            for _ in range(5):          # 5 次调用 = 1 次实际 eco 更新
                self.rm.update()

        after = self.rm.current_fertility[rid]
        self.assertGreater(after, before, "无再生时 fertility 应自然恢复")

    def test_recovery_amount_per_tick(self):
        """每 tick 恢复 FERTILITY_NATURAL_RECOVERY"""
        self._setup_fertility(0.9)
        rid = "test_region"
        self.rm.current_fertility[rid] = 0.5
        before = self.rm.current_fertility[rid]

        with patch('random.random', return_value=1.0):
            for _ in range(5):
                self.rm.update()

        self.assertAlmostEqual(
            self.rm.current_fertility[rid],
            before + FERTILITY_NATURAL_RECOVERY,
            msg=f"每 tick 应恢复 {FERTILITY_NATURAL_RECOVERY}",
        )

    # ── 边界截断 ──

    def test_fertility_clamped_upper(self):
        """fertility 不超过 base_fertility"""
        self._setup_fertility(0.6)
        rid = "test_region"
        # current 已达 base; recovery 不应推高
        self.rm.current_fertility[rid] = 0.6

        with patch('random.random', return_value=1.0):
            for _ in range(5):
                self.rm.update()

        self.assertAlmostEqual(self.rm.current_fertility[rid], 0.6,
                               msg="fertility 不应超过 base_fertility")

    def test_fertility_clamped_lower(self):
        """fertility 不低于 0.0 — update 中的保护性下限"""
        self._setup_fertility(0.6)
        rid = "test_region"
        # 设到异常值验证防御性 clamp（正常流程因 threshold 不会到负值）
        self.rm.current_fertility[rid] = -0.5

        with patch('random.random', return_value=1.0):  # 不再生
            for _ in range(5):
                self.rm.update()

        self.assertGreaterEqual(self.rm.current_fertility[rid], 0.0,
                                "fertility 不应低于 0.0")

    # ── 沙地禁区 ──

    def test_sand_no_mushroom(self):
        """沙地 (base_fertility=0.3) 不长蘑菇"""
        self._setup_fertility(0.3)
        with patch('random.random', return_value=0.0):
            self.rm._process_mushrooms()
        self.assertEqual(len(self.rm._mushrooms), 0,
                         "fertility=0.3 不应长出蘑菇")


if __name__ == "__main__":
    unittest.main()
