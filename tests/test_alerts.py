"""
Alert System 测试 — T-032

验证每种 Alert 的触发和不触发条件。
使用 mock/stub 对象，不依赖真实游戏类。
"""

import unittest

from systems.alerts import Alert, AlertManager, AlertSeverity, AlertType


# ── Mock 对象 ──

class MockResourceManager:
    """模拟 ResourceManager"""

    def __init__(self, total_food: int = 100):
        self._total_food = total_food

    def total_food_remaining(self) -> int:
        return self._total_food


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

    def region_name(self, rx: int, ry: int) -> str:
        names = {(0, 0): "plains", (1, 1): "forest_heart", (2, 2): "coast"}
        return names.get((rx, ry), f"({rx},{ry})")


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


class TestAlertTypes(unittest.TestCase):
    """AlertType 枚举完整性"""

    def test_all_types_present(self):
        """所有要求的 AlertType 都存在"""
        expected = {
            "ECO_COLLAPSE",
            "FOOD_SHORTAGE",
            "MIGRATION",
            "NPC_CONFLICT",
            "REGION_COLLAPSE",
            "REGRESSION_DETECTED",
            "FERTILITY_CRISIS",
        }
        actual = {e.name for e in AlertType}
        self.assertEqual(expected, actual)

    def test_all_severities_present(self):
        """所有要求的 AlertSeverity 都存在"""
        expected = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        actual = {e.name for e in AlertSeverity}
        self.assertEqual(expected, actual)


class TestAlertDataclass(unittest.TestCase):
    """Alert 数据类"""

    def test_to_dict(self):
        alert = Alert(
            type=AlertType.FOOD_SHORTAGE,
            severity=AlertSeverity.HIGH,
            data={"total_food": 3},
            tick=100,
            target_agents=["agent1"],
        )
        d = alert.to_dict()
        self.assertEqual(d["type"], "food_shortage")
        self.assertEqual(d["severity"], "high")
        self.assertEqual(d["data"]["total_food"], 3)
        self.assertEqual(d["tick"], 100)
        self.assertEqual(d["target_agents"], ["agent1"])

    def test_from_dict(self):
        d = {
            "type": "eco_collapse",
            "severity": "critical",
            "data": {"fertilities": {"plains": 0.2}},
            "tick": 50,
            "target_agents": ["agent_x"],
        }
        alert = Alert.from_dict(d)
        self.assertIs(alert.type, AlertType.ECO_COLLAPSE)
        self.assertIs(alert.severity, AlertSeverity.CRITICAL)
        self.assertEqual(alert.data["fertilities"]["plains"], 0.2)
        self.assertEqual(alert.tick, 50)
        self.assertEqual(alert.target_agents, ["agent_x"])


class TestEcoCollapse(unittest.TestCase):
    """ECO_COLLAPSE: 所有区域 fertility ≤ 0.3"""

    def test_triggers_when_all_low(self):
        """所有区域 fertility ≤ 0.3 时应触发 CRITICAL alert"""
        mgr = AlertManager()
        report = [
            {"name": "plains", "current_fertility": 0.2},
            {"name": "forest", "current_fertility": 0.1},
        ]
        pm = MockPressureMap(fertility_report=report)
        alerts = mgr.check_alerts(
            resource_mgr=MockResourceManager(),
            pressure_map=pm,
            npcs=[MockNPC()],
            time_system=MockTimeSystem(tick=100),
        )
        eco = [a for a in alerts if a.type == AlertType.ECO_COLLAPSE]
        self.assertEqual(len(eco), 1)
        self.assertIs(eco[0].severity, AlertSeverity.CRITICAL)
        self.assertEqual(eco[0].data["fertilities"]["plains"], 0.2)

    def test_not_triggered_when_any_above_threshold(self):
        """有任一区域 fertility > 0.3 时不触发"""
        mgr = AlertManager()
        report = [
            {"name": "plains", "current_fertility": 0.2},
            {"name": "forest", "current_fertility": 0.5},
        ]
        pm = MockPressureMap(fertility_report=report)
        alerts = mgr.check_alerts(
            resource_mgr=MockResourceManager(),
            pressure_map=pm,
            npcs=[MockNPC()],
            time_system=MockTimeSystem(),
        )
        eco = [a for a in alerts if a.type == AlertType.ECO_COLLAPSE]
        self.assertEqual(len(eco), 0)

    def test_not_triggered_with_empty_report(self):
        """fertility 报告为空时不触发"""
        mgr = AlertManager()
        pm = MockPressureMap(fertility_report=[])
        alerts = mgr.check_alerts(
            resource_mgr=MockResourceManager(),
            pressure_map=pm,
            npcs=[MockNPC()],
            time_system=MockTimeSystem(),
        )
        eco = [a for a in alerts if a.type == AlertType.ECO_COLLAPSE]
        self.assertEqual(len(eco), 0)

    def test_all_exactly_at_threshold(self):
        """所有区域 fertility == 0.3 时触发（边界值）"""
        mgr = AlertManager()
        report = [
            {"name": "plains", "current_fertility": 0.3},
            {"name": "forest", "current_fertility": 0.3},
        ]
        pm = MockPressureMap(fertility_report=report)
        alerts = mgr.check_alerts(
            resource_mgr=MockResourceManager(),
            pressure_map=pm,
            npcs=[MockNPC()],
            time_system=MockTimeSystem(),
        )
        eco = [a for a in alerts if a.type == AlertType.ECO_COLLAPSE]
        self.assertEqual(len(eco), 1)


class TestFoodShortage(unittest.TestCase):
    """FOOD_SHORTAGE: total_food < npc_count * 2"""

    def test_triggers_when_below_threshold(self):
        """总食物 < NPC数*2 时触发 HIGH alert"""
        mgr = AlertManager()
        rm = MockResourceManager(total_food=4)
        alerts = mgr.check_alerts(
            resource_mgr=rm,
            pressure_map=MockPressureMap(fertility_report=[{"name": "r", "current_fertility": 0.5}]),
            npcs=[MockNPC(), MockNPC(), MockNPC()],  # 3 npcs → threshold=6
            time_system=MockTimeSystem(),
        )
        food = [a for a in alerts if a.type == AlertType.FOOD_SHORTAGE]
        self.assertEqual(len(food), 1)
        self.assertIs(food[0].severity, AlertSeverity.HIGH)
        self.assertEqual(food[0].data["total_food"], 4)
        self.assertEqual(food[0].data["threshold"], 6)

    def test_not_triggered_when_sufficient(self):
        """总食物 >= NPC数*2 时不触发"""
        mgr = AlertManager()
        rm = MockResourceManager(total_food=10)
        alerts = mgr.check_alerts(
            resource_mgr=rm,
            pressure_map=MockPressureMap(fertility_report=[{"name": "r", "current_fertility": 0.5}]),
            npcs=[MockNPC(), MockNPC(), MockNPC()],  # threshold=6, food=10
            time_system=MockTimeSystem(),
        )
        food = [a for a in alerts if a.type == AlertType.FOOD_SHORTAGE]
        self.assertEqual(len(food), 0)

    def test_triggered_with_single_npc(self):
        """单个 NPC 时仍有正确阈值"""
        mgr = AlertManager()
        rm = MockResourceManager(total_food=1)
        alerts = mgr.check_alerts(
            resource_mgr=rm,
            pressure_map=MockPressureMap(fertility_report=[{"name": "r", "current_fertility": 0.5}]),
            npcs=[MockNPC()],
            time_system=MockTimeSystem(),
        )
        food = [a for a in alerts if a.type == AlertType.FOOD_SHORTAGE]
        self.assertEqual(len(food), 1)
        self.assertEqual(food[0].data["threshold"], 2)

    def test_no_npcs_no_alert(self):
        """NPC 列表为空时不触发"""
        mgr = AlertManager()
        rm = MockResourceManager(total_food=0)
        alerts = mgr.check_alerts(
            resource_mgr=rm,
            pressure_map=MockPressureMap(fertility_report=[{"name": "r", "current_fertility": 0.5}]),
            npcs=[],
            time_system=MockTimeSystem(),
        )
        food = [a for a in alerts if a.type == AlertType.FOOD_SHORTAGE]
        self.assertEqual(len(food), 0)


class TestRegionCollapse(unittest.TestCase):
    """REGION_COLLAPSE: 某区域 pressure > 0.9 连续 100 tick"""

    def test_triggers_after_100_ticks(self):
        """区域高压持续 100 tick 后触发 HIGH alert"""
        mgr = AlertManager()
        pm = MockPressureMap(
            fertility_report=[{"name": "forest_heart", "current_fertility": 0.3}],
            top_pressure=[((1, 1), 0.95)],
        )
        npcs = [MockNPC()]

        # 前 99 tick 不触发
        for _ in range(99):
            alerts = mgr.check_alerts(
                resource_mgr=MockResourceManager(),
                pressure_map=pm,
                npcs=npcs,
                time_system=MockTimeSystem(),
            )
            collapse = [a for a in alerts if a.type == AlertType.REGION_COLLAPSE]
            self.assertEqual(len(collapse), 0, f"unexpected alert at tick before 100")

        # 第 100 tick 触发
        alerts = mgr.check_alerts(
            resource_mgr=MockResourceManager(),
            pressure_map=pm,
            npcs=npcs,
            time_system=MockTimeSystem(),
        )
        collapse = [a for a in alerts if a.type == AlertType.REGION_COLLAPSE]
        self.assertEqual(len(collapse), 1)
        self.assertIs(collapse[0].severity, AlertSeverity.HIGH)
        self.assertEqual(collapse[0].data["region"], [1, 1])
        self.assertEqual(collapse[0].data["region_name"], "forest_heart")

    def test_not_triggered_when_pressure_drops(self):
        """中间压力下降后计数器重置，不触发"""
        mgr = AlertManager()
        pm_high = MockPressureMap(
            fertility_report=[{"name": "plains", "current_fertility": 0.5}],
            top_pressure=[((0, 0), 0.95)],
        )
        pm_low = MockPressureMap(
            fertility_report=[{"name": "plains", "current_fertility": 0.5}],
            top_pressure=[((0, 0), 0.5)],
        )
        npcs = [MockNPC()]

        # 50 tick 高压
        for _ in range(50):
            mgr.check_alerts(MockResourceManager(), pm_high, npcs, MockTimeSystem())

        # 压力下降
        for _ in range(10):
            mgr.check_alerts(MockResourceManager(), pm_low, npcs, MockTimeSystem())

        # 再 60 tick 高压 → 计数器应从0开始，总计110 tick但连续高压只有60
        for _ in range(60):
            mgr.check_alerts(MockResourceManager(), pm_high, npcs, MockTimeSystem())

        # 不应触发（连续高压最多 60 tick，未到 100）
        alerts = mgr.check_alerts(MockResourceManager(), pm_high, npcs, MockTimeSystem())
        collapse = [a for a in alerts if a.type == AlertType.REGION_COLLAPSE]
        self.assertEqual(len(collapse), 0)

    def test_multiple_regions_independent(self):
        """多个高压区域各自独立计数"""
        mgr = AlertManager()
        pm = MockPressureMap(
            fertility_report=[{"name": "r1", "current_fertility": 0.5},
                              {"name": "r2", "current_fertility": 0.5}],
            top_pressure=[((0, 0), 0.95), ((1, 1), 0.95)],
        )
        npcs = [MockNPC()]

        # 持续 99 tick，第 100 次检查触发
        for _ in range(99):
            mgr.check_alerts(MockResourceManager(), pm, npcs, MockTimeSystem())

        alerts = mgr.check_alerts(MockResourceManager(), pm, npcs, MockTimeSystem())
        collapses = [a for a in alerts if a.type == AlertType.REGION_COLLAPSE]
        self.assertEqual(len(collapses), 2)


class TestFertilityCrisis(unittest.TestCase):
    """FERTILITY_CRISIS: 平均 fertility < 0.2"""

    def test_triggers_when_avg_below_threshold(self):
        """平均 fertility < 0.2 时触发 CRITICAL alert"""
        mgr = AlertManager()
        report = [
            {"name": "plains", "current_fertility": 0.15},
            {"name": "forest", "current_fertility": 0.19},
        ]
        pm = MockPressureMap(fertility_report=report)
        alerts = mgr.check_alerts(
            resource_mgr=MockResourceManager(),
            pressure_map=pm,
            npcs=[MockNPC()],
            time_system=MockTimeSystem(),
        )
        crisis = [a for a in alerts if a.type == AlertType.FERTILITY_CRISIS]
        self.assertEqual(len(crisis), 1)
        self.assertIs(crisis[0].severity, AlertSeverity.CRITICAL)
        self.assertAlmostEqual(crisis[0].data["average_fertility"], 0.17)

    def test_not_triggered_when_avg_at_or_above(self):
        """平均 fertility >= 0.2 时不触发"""
        mgr = AlertManager()
        report = [
            {"name": "plains", "current_fertility": 0.2},
            {"name": "forest", "current_fertility": 0.3},
        ]
        pm = MockPressureMap(fertility_report=report)
        alerts = mgr.check_alerts(
            resource_mgr=MockResourceManager(),
            pressure_map=pm,
            npcs=[MockNPC()],
            time_system=MockTimeSystem(),
        )
        crisis = [a for a in alerts if a.type == AlertType.FERTILITY_CRISIS]
        self.assertEqual(len(crisis), 0)

    def test_not_triggered_with_empty_report(self):
        """fertility 报告为空时不触发"""
        mgr = AlertManager()
        pm = MockPressureMap(fertility_report=[])
        alerts = mgr.check_alerts(
            resource_mgr=MockResourceManager(),
            pressure_map=pm,
            npcs=[MockNPC()],
            time_system=MockTimeSystem(),
        )
        crisis = [a for a in alerts if a.type == AlertType.FERTILITY_CRISIS]
        self.assertEqual(len(crisis), 0)


class TestMultipleAlertsSimultaneous(unittest.TestCase):
    """多个 Alert 同时触发"""

    def test_multiple_alerts_in_one_check(self):
        """模拟极端场景：多项条件同时满足"""
        mgr = AlertManager()
        rm = MockResourceManager(total_food=0)
        report = [
            {"name": "plains", "current_fertility": 0.1},
            {"name": "forest", "current_fertility": 0.1},
        ]
        pm = MockPressureMap(
            fertility_report=report,
            top_pressure=[((0, 0), 0.95)],
        )
        npcs = [MockNPC()]

        # Tick 1~99: 持续高压，第 100 次触发
        for _ in range(99):
            mgr.check_alerts(rm, pm, npcs, MockTimeSystem())

        # 第 100 次检查触发 REGION_COLLAPSE
        alerts = mgr.check_alerts(rm, pm, npcs, MockTimeSystem())

        types_found = {a.type for a in alerts}
        # ECO_COLLAPSE + FOOD_SHORTAGE + REGION_COLLAPSE (100 tick) + FERTILITY_CRISIS
        self.assertIn(AlertType.ECO_COLLAPSE, types_found)
        self.assertIn(AlertType.FOOD_SHORTAGE, types_found)
        self.assertIn(AlertType.REGION_COLLAPSE, types_found)
        self.assertIn(AlertType.FERTILITY_CRISIS, types_found)


class TestAlertYamlSerialization(unittest.TestCase):
    """Alert YAML 序列化能力"""

    def test_to_dict_roundtrip(self):
        """Alert → dict → Alert 保留所有字段"""
        original = Alert(
            type=AlertType.MIGRATION,
            severity=AlertSeverity.LOW,
            data={"direction": "north"},
            tick=42,
            target_agents=["npc_1"],
        )
        d = original.to_dict()
        restored = Alert.from_dict(d)
        self.assertEqual(original.type, restored.type)
        self.assertEqual(original.severity, restored.severity)
        self.assertEqual(original.data, restored.data)
        self.assertEqual(original.tick, restored.tick)
        self.assertEqual(original.target_agents, restored.target_agents)

    def test_to_dict_yaml_serializable(self):
        """to_dict() 输出可被 yaml.dump 序列化"""
        import yaml
        alert = Alert(
            type=AlertType.REGION_COLLAPSE,
            severity=AlertSeverity.HIGH,
            data={"region": [1, 1], "pressure": 0.95},
            tick=100,
        )
        d = alert.to_dict()
        # 应无异常
        yaml_output = yaml.dump(d, default_flow_style=False)
        self.assertIn("region_collapse", yaml_output)
        self.assertIn("high", yaml_output)


class TestAlertDefaults(unittest.TestCase):
    """Alert 默认值"""

    def test_default_fields(self):
        """默认 tick=0, data={}, target_agents=[]"""
        alert = Alert(type=AlertType.MIGRATION, severity=AlertSeverity.LOW)
        self.assertEqual(alert.tick, 0)
        self.assertEqual(alert.data, {})
        self.assertEqual(alert.target_agents, [])


if __name__ == "__main__":
    unittest.main()
