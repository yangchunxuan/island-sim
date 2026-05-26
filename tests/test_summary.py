"""
Summary Layer 测试 — T-032

验证 WorldSummary 生成正确的摘要结构。
使用 mock/stub 对象，不依赖真实游戏类。
"""

import os
import tempfile
import unittest

import yaml

from systems.summary import WorldSummary


# ── Mock 对象 ──

class MockResourceManager:
    """模拟 ResourceManager"""

    def __init__(self, total_food: int = 50,
                 forests: list[tuple[int, int]] | None = None,
                 mushrooms: list[tuple[int, int, str]] | None = None,
                 fish: list[tuple[int, int]] | None = None):
        self._total_food = total_food
        self._forests = forests or []
        self._mushrooms = mushrooms or []
        self._fish = fish or []

    def total_food_remaining(self) -> int:
        return self._total_food

    def available_forests(self) -> list[tuple[int, int]]:
        return self._forests

    def available_mushrooms(self) -> list[tuple[int, int, str]]:
        return self._mushrooms

    def available_fish(self) -> list[tuple[int, int]]:
        return self._fish


class MockPressureMap:
    """模拟 RegionPressureMap"""

    def __init__(self, fertility_report: list[dict] | None = None,
                 top_pressure: list[tuple[tuple[int, int], float]] | None = None):
        self._fertility_report = fertility_report or []
        self._top_pressure = top_pressure or []

    def get_fertility_report(self) -> list[dict]:
        return self._fertility_report

    def get_top_pressure(self, n: int = 3) -> list[tuple[tuple[int, int], float]]:
        return self._top_pressure[:n]


class MockNPC:
    """模拟 NPC"""

    def __init__(self, hunger: float = 50, state: str = "IDLE", weakened: bool = False):
        self.hunger = hunger
        self._state = state
        self._weakened = weakened

    def get_state(self) -> str:
        return self._state


class MockTimeSystem:
    """模拟 TimeSystem"""

    def __init__(self, tick: int = 0):
        self._tick_count = tick

    def get_day_count(self) -> int:
        return self._tick_count // 1200

    def get_season(self) -> str:
        return "spring"


class TestWorldSummaryBasic(unittest.TestCase):
    """WorldSummary 基本结构"""

    def setUp(self):
        self.rm = MockResourceManager(
            total_food=30,
            forests=[(5, 5), (6, 5)],
            mushrooms=[(3, 3, "fresh")],
            fish=[(1, 1)],
        )
        self.pm = MockPressureMap(
            fertility_report=[
                {"name": "plains", "current_fertility": 0.6},
                {"name": "forest_heart", "current_fertility": 0.8},
            ],
            top_pressure=[((1, 1), 0.45), ((0, 0), 0.3)],
        )
        self.npcs = [
            MockNPC(hunger=30, state="IDLE"),
            MockNPC(hunger=65, state="WALK", weakened=True),
            MockNPC(hunger=10, state="SLEEP"),
        ]
        self.ts = MockTimeSystem(tick=3600)

    def test_summary_has_required_keys(self):
        """摘要输出包含所有必需的顶层键"""
        data = WorldSummary.generate(self.rm, self.pm, self.npcs, self.ts)
        required_keys = {
            "tick", "day", "season", "ecology_pressure",
            "avg_fertility", "food_supply", "migration_trend",
            "npc_status",
        }
        self.assertTrue(required_keys.issubset(data.keys()), f"Missing keys: {required_keys - data.keys()}")

    def test_tick_and_day(self):
        """时间信息正确"""
        data = WorldSummary.generate(self.rm, self.pm, self.npcs, self.ts)
        self.assertEqual(data["tick"], 3600)
        # 3600 / 1200 = 3
        self.assertEqual(data["day"], 3)
        self.assertEqual(data["season"], "spring")

    def test_avg_fertility(self):
        """平均地力计算正确"""
        data = WorldSummary.generate(self.rm, self.pm, self.npcs, self.ts)
        self.assertAlmostEqual(data["avg_fertility"], 0.7)  # (0.6 + 0.8) / 2

    def test_food_supply(self):
        """食物供应信息正确"""
        data = WorldSummary.generate(self.rm, self.pm, self.npcs, self.ts)
        fs = data["food_supply"]
        self.assertEqual(fs["forests"], 2)
        self.assertEqual(fs["mushrooms"], 1)
        self.assertEqual(fs["fish"], 1)
        self.assertEqual(fs["total"], 30)

    def test_ecology_pressure(self):
        """生态压力 TOP 3"""
        data = WorldSummary.generate(self.rm, self.pm, self.npcs, self.ts)
        pressure = data["ecology_pressure"]
        self.assertEqual(len(pressure), 2)
        self.assertEqual(pressure[0]["region"], [1, 1])
        self.assertAlmostEqual(pressure[0]["score"], 0.45)

    def test_npc_status(self):
        """NPC 状态统计"""
        data = WorldSummary.generate(self.rm, self.pm, self.npcs, self.ts)
        ns = data["npc_status"]
        self.assertEqual(ns["alive"], 3)
        self.assertEqual(ns["weakened"], 1)
        self.assertAlmostEqual(ns["avg_hunger"], 35.0)  # (30 + 65 + 10) / 3

    def test_migration_trend_stable(self):
        """压力较低时 migration_trend 为 stable"""
        pm_low = MockPressureMap(
            fertility_report=[{"name": "r", "current_fertility": 0.8}],
            top_pressure=[((0, 0), 0.3)],
        )
        data = WorldSummary.generate(self.rm, pm_low, self.npcs, self.ts)
        self.assertEqual(data["migration_trend"], "stable")

    def test_migration_trend_mild(self):
        """中等压力时 migration_trend 为 mild_pressure"""
        pm_mid = MockPressureMap(
            fertility_report=[{"name": "r", "current_fertility": 0.5}],
            top_pressure=[((0, 0), 0.6)],
        )
        data = WorldSummary.generate(self.rm, pm_mid, self.npcs, self.ts)
        self.assertEqual(data["migration_trend"], "mild_pressure")

    def test_migration_trend_outward(self):
        """高压时 migration_trend 为 outward_pressure"""
        pm_high = MockPressureMap(
            fertility_report=[{"name": "r", "current_fertility": 0.2}],
            top_pressure=[((0, 0), 0.85)],
        )
        data = WorldSummary.generate(self.rm, pm_high, self.npcs, self.ts)
        self.assertEqual(data["migration_trend"], "outward_pressure")


class TestWorldSummaryEmptyNPCs(unittest.TestCase):
    """空 NPC 列表时的边界行为"""

    def test_empty_npcs(self):
        """没有 NPC 时 npc_status 为零值"""
        data = WorldSummary.generate(
            resource_mgr=MockResourceManager(),
            pressure_map=MockPressureMap(
                fertility_report=[{"name": "r", "current_fertility": 0.5}],
            ),
            npcs=[],
            time_system=MockTimeSystem(),
        )
        ns = data["npc_status"]
        self.assertEqual(ns["alive"], 0)
        self.assertEqual(ns["weakened"], 0)
        self.assertEqual(ns["avg_hunger"], 0.0)


class TestWorldSummaryEmptyFertility(unittest.TestCase):
    """空 fertility 报告时的边界行为"""

    def test_empty_fertility_report(self):
        """无 fertility 报告时 avg_fertility 为 0"""
        data = WorldSummary.generate(
            resource_mgr=MockResourceManager(total_food=10),
            pressure_map=MockPressureMap(fertility_report=[]),
            npcs=[MockNPC()],
            time_system=MockTimeSystem(),
        )
        self.assertEqual(data["avg_fertility"], 0.0)
        self.assertEqual(data["ecology_pressure"], [])


class TestWorldSummaryWithAlerts(unittest.TestCase):
    """带 Alert 的摘要"""

    def test_top_alerts_included_when_provided(self):
        """提供 alerts 时，top_alerts 出现在摘要中"""
        from systems.alerts import Alert, AlertType, AlertSeverity

        alerts = [
            Alert(type=AlertType.FOOD_SHORTAGE, severity=AlertSeverity.HIGH,
                  data={"total_food": 2}, tick=10),
        ]
        data = WorldSummary.generate(
            resource_mgr=MockResourceManager(total_food=2),
            pressure_map=MockPressureMap(
                fertility_report=[{"name": "r", "current_fertility": 0.5}],
            ),
            npcs=[MockNPC()],
            time_system=MockTimeSystem(tick=10),
            alerts=alerts,
        )
        self.assertIn("top_alerts", data)
        self.assertEqual(len(data["top_alerts"]), 1)
        self.assertEqual(data["top_alerts"][0]["type"], "food_shortage")
        self.assertEqual(data["top_alerts"][0]["severity"], "high")

    def test_no_top_alerts_when_not_provided(self):
        """不提供 alerts 时摘要不含 top_alerts"""
        data = WorldSummary.generate(
            resource_mgr=MockResourceManager(),
            pressure_map=MockPressureMap(
                fertility_report=[{"name": "r", "current_fertility": 0.5}],
            ),
            npcs=[MockNPC()],
            time_system=MockTimeSystem(),
        )
        self.assertNotIn("top_alerts", data)


class TestWorldSummaryWrite(unittest.TestCase):
    """write_summary 输出 YAML 文件"""

    def test_write_summary_creates_yaml(self):
        """write_summary 写入合法的 YAML 文件"""
        data = {
            "tick": 100,
            "day": 0,
            "season": "spring",
            "ecology_pressure": [],
            "avg_fertility": 0.5,
            "food_supply": {"forests": 0, "mushrooms": 0, "fish": 0, "total": 0},
            "migration_trend": "stable",
            "npc_status": {"alive": 0, "weakened": 0, "avg_hunger": 0.0},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            tmp_path = f.name

        try:
            WorldSummary.write_summary(tmp_path, data)
            with open(tmp_path, "r") as f:
                loaded = yaml.safe_load(f)
            self.assertEqual(loaded["tick"], 100)
            self.assertEqual(loaded["season"], "spring")
            self.assertEqual(loaded["npc_status"]["alive"], 0)
        finally:
            os.unlink(tmp_path)


class TestWorldSummaryAllFieldsNumeric(unittest.TestCase):
    """所有数值字段为合法类型"""

    def test_all_fields_are_serializable_types(self):
        """所有字段应是 int / float / str / list / dict"""
        data = WorldSummary.generate(
            resource_mgr=MockResourceManager(total_food=42,
                                              forests=[(0, 0)],
                                              mushrooms=[(1, 0, "fresh")],
                                              fish=[(2, 0)]),
            pressure_map=MockPressureMap(
                fertility_report=[{"name": "p", "current_fertility": 0.55}],
                top_pressure=[((0, 0), 0.3)],
            ),
            npcs=[MockNPC(hunger=50), MockNPC(hunger=70)],
            time_system=MockTimeSystem(tick=2400),
        )
        # Test types are yaml-compatible
        yaml_str = yaml.dump(data, default_flow_style=False)
        self.assertIsInstance(yaml_str, str)
        self.assertIn("tick: 2400", yaml_str)
        self.assertIn("avg_hunger: 60.0", yaml_str)


if __name__ == "__main__":
    unittest.main()
