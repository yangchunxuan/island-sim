"""
观察系统测试 — Island Sim v1

验证：事件记录、裁剪、模式分析、叙事生成、WorldObserver事件检测。
"""

import os
import shutil
import unittest

from config import FOOD_PER_FOREST, TileType
from observer import EventLogger, LongTermMemory, PatternAnalyzer, NarrativeGenerator, WorldObserver
from observer.narrative_generator import REPORT_DIR


# ═══════════════════════════════════════════════
# EventLogger 测试
# ═══════════════════════════════════════════════

class TestEventLogger(unittest.TestCase):
    """事件记录器基础测试"""

    def setUp(self):
        self.logger = EventLogger()

    def test_log_appends_event(self):
        self.logger.log(tick=0, event_type="TEST", npc="A")
        self.assertEqual(self.logger.count, 1)

    def test_log_event_format(self):
        self.logger.log(tick=42, event_type="NPC_EAT", npc="A-Qiang",
                        position=(5, 5), details={"hunger_drop": 10})
        event = self.logger.get_events()[0]
        self.assertEqual(event["tick"], 42)
        self.assertEqual(event["event_type"], "NPC_EAT")
        self.assertEqual(event["npc"], "A-Qiang")
        self.assertEqual(event["position"], (5, 5))
        self.assertEqual(event["details"]["hunger_drop"], 10)

    def test_get_events_by_type(self):
        self.logger.log(tick=0, event_type="NPC_EAT", npc="A")
        self.logger.log(tick=0, event_type="NPC_EAT", npc="B")
        self.logger.log(tick=0, event_type="NPC_SLEEP", npc="C")
        eats = self.logger.get_events_by_type("NPC_EAT")
        self.assertEqual(len(eats), 2)

    def test_get_events_since(self):
        self.logger.log(tick=10, event_type="A")
        self.logger.log(tick=20, event_type="B")
        self.logger.log(tick=30, event_type="C")
        recent = self.logger.get_events_since(20)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]["event_type"], "B")

    def test_max_events_enforced(self):
        for i in range(5010):
            self.logger.log(tick=i, event_type="BULK")
        self.assertLessEqual(self.logger.count, 5000)
        # 最早的事件应被丢弃
        first_remaining = self.logger.get_events()[0]
        self.assertGreater(first_remaining["tick"], 0)

    def test_clear(self):
        self.logger.log(tick=0, event_type="X")
        self.logger.clear()
        self.assertEqual(self.logger.count, 0)


# ═══════════════════════════════════════════════
# PatternAnalyzer 测试
# ═══════════════════════════════════════════════

class TestPatternAnalyzer(unittest.TestCase):
    """模式分析器测试"""

    def setUp(self):
        self.logger = EventLogger()
        self.analyzer = PatternAnalyzer(self.logger)

    def test_analyze_returns_report_structure(self):
        report = self.analyzer.analyze(tick=1200, npcs=[], resource_mgr=_FakeResource())
        self.assertIn("day", report)
        self.assertIn("hot_regions", report)
        self.assertIn("npc_tendencies", report)
        self.assertIn("resource_trends", report)
        self.assertIn("world_pressure", report)

    def test_hot_regions_from_events(self):
        self.logger.log(tick=100, event_type="NPC_MOVE_REGION",
                        npc="A", details={"to": "西北"})
        self.logger.log(tick=101, event_type="NPC_MOVE_REGION",
                        npc="A", details={"to": "西北"})
        self.logger.log(tick=102, event_type="NPC_MOVE_REGION",
                        npc="B", details={"to": "东南"})
        report = self.analyzer.analyze(tick=1200, npcs=[], resource_mgr=_FakeResource())
        regions = report["hot_regions"]
        self.assertTrue(len(regions) >= 1)
        self.assertEqual(regions[0]["name"], "西北")

    def test_npc_tendencies(self):
        class FakeWeakenedNPC:
            name = "TestNPC"
            def get_state(self): return "IDLE"
            hunger = 70
            energy = 50
            mood = 30
            _weakened = True

        report = self.analyzer.analyze(tick=1200, npcs=[FakeWeakenedNPC()],
                                       resource_mgr=_FakeResource())
        tendencies = report["npc_tendencies"]
        self.assertEqual(len(tendencies), 1)
        self.assertTrue(tendencies[0]["weakened"])
        self.assertEqual(tendencies[0]["hunger"], 70)

    def test_resource_trends(self):
        rm = _FakeResource(total_food=9, depleted_count=2,
                           forest_count=10, depleted_forests={(0, 0), (1, 1)})
        report = self.analyzer.analyze(tick=1200, npcs=[], resource_mgr=rm)
        rt = report["resource_trends"]
        self.assertEqual(rt["total_food"], 9)
        self.assertEqual(rt["depleted_count"], 2)
        self.assertAlmostEqual(rt["depletion_rate"], 0.2)

    def test_world_pressure(self):
        class NPC:
            name = "X"
            hunger = 80
            energy = 40
            mood = 20
            _weakened = True
            def get_state(self): return "IDLE"

        report = self.analyzer.analyze(tick=1200, npcs=[NPC()],
                                       resource_mgr=_FakeResource())
        wp = report["world_pressure"]
        self.assertEqual(wp["avg_hunger"], 80)
        self.assertEqual(wp["weakened_count"], 1)
        self.assertEqual(wp["avg_mood"], 20)


# ═══════════════════════════════════════════════
# NarrativeGenerator 测试
# ═══════════════════════════════════════════════

class TestNarrativeGenerator(unittest.TestCase):
    """叙事生成器测试"""

    @classmethod
    def setUpClass(cls):
        os.makedirs(REPORT_DIR, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(REPORT_DIR):
            shutil.rmtree(REPORT_DIR)

    def setUp(self):
        self.narrator = NarrativeGenerator()

    def test_generate_creates_report_file(self):
        report = {
            "day": 5, "tick": 6000,
            "hot_regions": [{"name": "东南", "count": 30, "ratio": 0.6}],
            "npc_tendencies": [],
            "resource_trends": {"total_food": 15, "depleted_count": 1,
                               "depletion_rate": 0.1, "recovery_active": True,
                               "mushroom_activity": 5, "fish_activity": 3},
            "world_pressure": {"avg_hunger": 35, "avg_energy": 60,
                               "avg_mood": 55, "weakened_count": 1, "npc_count": 5},
        }
        text = self.narrator.generate(6000, report)
        self.assertTrue(len(text) > 0)
        self.assertTrue(self.narrator.report_exists(5))

    def test_no_fabrication(self):
        """所有narrative文本必须基于报告数据中的字段生成"""
        report = {
            "day": 1, "tick": 1200,
            "hot_regions": [],
            "npc_tendencies": [],
            "resource_trends": {"total_food": 30, "depleted_count": 0,
                               "depletion_rate": 0.0, "recovery_active": False,
                               "mushroom_activity": 0, "fish_activity": 0},
            "world_pressure": {"avg_hunger": 50, "avg_energy": 60,
                               "avg_mood": 50, "weakened_count": 0, "npc_count": 5},
        }
        text = self.narrator.generate(1200, report)
        # 不应包含"不存在"或编造的内容
        self.assertNotIn("不存在", text)
        self.assertNotIn("奇迹", text)
        self.assertNotIn("神秘", text)
        # 应包含合理内容或默认消息
        self.assertTrue(len(text) > 0)

    def test_generate_no_events_fallback(self):
        report = {
            "day": 0, "tick": 1,
            "hot_regions": [], "npc_tendencies": [],
            "resource_trends": {"total_food": 30, "depleted_count": 0,
                               "depletion_rate": 0.0, "recovery_active": False,
                               "mushroom_activity": 0, "fish_activity": 0},
            "world_pressure": {"avg_hunger": 50, "avg_energy": 60,
                               "avg_mood": 50, "weakened_count": 0, "npc_count": 5},
        }
        text = self.narrator.generate(1, report)
        self.assertEqual(text, "今日无显著事件发生。")

    def test_high_pressure_narrative(self):
        report = {
            "day": 3, "tick": 3600,
            "hot_regions": [], "npc_tendencies": [],
            "resource_trends": {"total_food": 3, "depleted_count": 8,
                               "depletion_rate": 0.6, "recovery_active": False,
                               "mushroom_activity": 1, "fish_activity": 0},
            "world_pressure": {"avg_hunger": 75, "avg_energy": 30,
                               "avg_mood": 25, "weakened_count": 3, "npc_count": 5},
        }
        text = self.narrator.generate(3600, report)
        self.assertIn("长期枯竭", text)
        self.assertIn("weakened", text)
        self.assertIn("压力", text)

    def test_full_day_12_narrative(self):
        """模拟Day 12的综合叙事"""
        report = {
            "day": 12, "tick": 14400,
            "hot_regions": [{"name": "东南", "count": 45, "ratio": 0.55}],
            "npc_tendencies": [
                {"name": "阿强", "state": "WALK", "weakened": False,
                 "hunger": 40, "mood": 60, "coastal_tendency": True,
                 "recent_moves": 20},
                {"name": "小美", "state": "IDLE", "weakened": False,
                 "hunger": 35, "mood": 70, "coastal_tendency": True,
                 "recent_moves": 15},
            ],
            "resource_trends": {"total_food": 5, "depleted_count": 6,
                               "depletion_rate": 0.4, "recovery_active": False,
                               "mushroom_activity": 10, "fish_activity": 8},
            "world_pressure": {"avg_hunger": 55, "avg_energy": 50,
                               "avg_mood": 45, "weakened_count": 1, "npc_count": 5},
        }
        text = self.narrator.generate(14400, report)
        self.assertIn("海岸觅食路线", text)
        self.assertIn("阿强", text)
        self.assertIn("小美", text)


# ═══════════════════════════════════════════════
# WorldObserver 事件检测测试
# ═══════════════════════════════════════════════

class TestWorldObserverEventDetection(unittest.TestCase):
    """WorldObserver事件检测测试"""

    def setUp(self):
        self.obs = WorldObserver()

    def _rm_with_forest(self):
        grid = [[TileType.GRASS for _ in range(20)] for _ in range(20)]
        grid[5][5] = TileType.FOREST
        from world.resources import ResourceManager
        rm = ResourceManager(grid)
        return rm, grid

    class _SimpleNPC:
        def __init__(self, name="TestNPC", x=0, y=0, state="IDLE",
                     hunger=50, energy=70, mood=60, weakened=False):
            self.name = name
            self.x = x
            self.y = y
            self.hunger = hunger
            self.energy = energy
            self.mood = mood
            self._weakened = weakened
            self._state = state
        def get_state(self):
            return self._state

    def test_detect_resource_depletion(self):
        """RESOURCE_DEPLETED: 森林食物耗尽后触发"""
        rm, grid = self._rm_with_forest()
        # 第一帧建立快照
        self.obs.update(tick=1, resource_mgr=rm, npcs=[])
        # 耗尽森林
        for _ in range(FOOD_PER_FOREST):
            rm.collect(5, 5)
        # 检测
        self.obs.update(tick=10, resource_mgr=rm, npcs=[])
        events = self.obs.event_logger.get_events_by_type("RESOURCE_DEPLETED")
        self.assertTrue(len(events) >= 1)
        self.assertEqual(events[0]["position"], (5, 5))

    def test_detect_mushroom_spawn(self):
        """MUSHROOM_SPAWN: 蘑菇生成后触发"""
        rm, grid = self._rm_with_forest()
        self.obs.update(tick=1, resource_mgr=rm, npcs=[])
        rm._mushrooms[(3, 3)] = {"age": 0}
        self.obs.update(tick=10, resource_mgr=rm, npcs=[])
        events = self.obs.event_logger.get_events_by_type("MUSHROOM_SPAWN")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["position"], (3, 3))

    def test_detect_fish_spawn(self):
        """FISH_SPAWN: 鱼生成后触发"""
        rm, grid = self._rm_with_forest()
        self.obs.update(tick=1, resource_mgr=rm, npcs=[])
        rm._fish[(7, 7)] = {"age": 0}
        self.obs.update(tick=10, resource_mgr=rm, npcs=[])
        events = self.obs.event_logger.get_events_by_type("FISH_SPAWN")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["position"], (7, 7))

    def test_detect_npc_enter_weakened(self):
        """NPC_ENTER_WEAKENED: NPC进入weakened状态后触发"""
        npc = self._SimpleNPC(weakened=False)
        self.obs.update(tick=1, resource_mgr=None, npcs=[npc])
        npc._weakened = True
        npc.hunger = 85
        self.obs.update(tick=10, resource_mgr=None, npcs=[npc])
        events = self.obs.event_logger.get_events_by_type("NPC_ENTER_WEAKENED")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["npc"], "TestNPC")

    def test_detect_npc_recover_weakened(self):
        """NPC_RECOVER_WEAKENED: NPC恢复后触发"""
        npc = self._SimpleNPC(weakened=True)
        self.obs.update(tick=1, resource_mgr=None, npcs=[npc])
        npc._weakened = False
        npc.hunger = 40
        self.obs.update(tick=10, resource_mgr=None, npcs=[npc])
        events = self.obs.event_logger.get_events_by_type("NPC_RECOVER_WEAKENED")
        self.assertEqual(len(events), 1)

    def test_detect_npc_eat(self):
        """NPC_EAT: NPC吃完后触发"""
        npc = self._SimpleNPC(state="EAT", hunger=60)
        self.obs.update(tick=1, resource_mgr=None, npcs=[npc])
        npc._state = "IDLE"
        npc.hunger = 30
        self.obs.update(tick=10, resource_mgr=None, npcs=[npc])
        events = self.obs.event_logger.get_events_by_type("NPC_EAT")
        self.assertEqual(len(events), 1)
        self.assertGreater(events[0]["details"]["hunger_drop"], 0)

    def test_detect_npc_sleep(self):
        """NPC_SLEEP: NPC开始睡觉后触发"""
        npc = self._SimpleNPC(state="IDLE")
        self.obs.update(tick=1, resource_mgr=None, npcs=[npc])
        npc._state = "SLEEP"
        npc.energy = 20
        self.obs.update(tick=10, resource_mgr=None, npcs=[npc])
        events = self.obs.event_logger.get_events_by_type("NPC_SLEEP")
        self.assertEqual(len(events), 1)

    def test_detect_npc_move_region(self):
        """NPC_MOVE_REGION: NPC跨区域移动后触发"""
        npc = self._SimpleNPC(x=0, y=0)
        self.obs.update(tick=1, resource_mgr=None, npcs=[npc])
        npc.x = 15
        npc.y = 15
        self.obs.update(tick=10, resource_mgr=None, npcs=[npc])
        events = self.obs.event_logger.get_events_by_type("NPC_MOVE_REGION")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["details"]["from"], "西北")
        self.assertEqual(events[0]["details"]["to"], "东南")

    def test_first_tick_no_events(self):
        """第一帧只记录NPC_BEHAVIOR_PROFILE（不记录NPC状态事件，prev为空）"""
        npc = self._SimpleNPC()
        rm, grid = self._rm_with_forest()
        self.obs.update(tick=0, resource_mgr=rm, npcs=[npc])
        # 唯一的事件是NPC_BEHAVIOR_PROFILE
        self.assertEqual(self.obs.event_logger.count, 1)
        events = self.obs.event_logger.get_events_since(0)
        self.assertEqual(events[0]["event_type"], "NPC_BEHAVIOR_PROFILE")

    def test_periodic_analysis_triggers_narrative(self):
        """每1200tick触发模式分析和叙事生成"""
        rm, grid = self._rm_with_forest()
        for t in range(1, 2401):
            self.obs.update(tick=t, resource_mgr=rm, npcs=[])
        # 至少有一次分析报告
        self.assertIsNotNone(self.obs.last_report)
        day1_report = os.path.join(REPORT_DIR, "day_001.md")
        self.assertTrue(os.path.exists(day1_report))


# ═══════════════════════════════════════════════
# LongTermMemory 测试
# ═══════════════════════════════════════════════

class TestLongTermMemory(unittest.TestCase):
    """长期记忆统计测试"""

    def setUp(self):
        self.mem = LongTermMemory(path="/tmp/test_world_memory.json")
        if os.path.exists("/tmp/test_world_memory.json"):
            os.remove("/tmp/test_world_memory.json")

    def tearDown(self):
        if os.path.exists("/tmp/test_world_memory.json"):
            os.remove("/tmp/test_world_memory.json")

    def test_initial_state(self):
        self.assertEqual(self.mem.all_time_max_hunger, 0.0)
        self.assertEqual(self.mem.total_collapses, 0)
        self.assertEqual(self.mem.days_simulated, 0)

    def test_tracks_max_hunger(self):
        class FakeNPC:
            name, hunger, mood = "阿强", 95, 30
        self.mem.update(tick=1200, npcs=[FakeNPC()])
        summary = self.mem.get_summary()
        self.assertEqual(summary["all_time_max_hunger"], 95)
        self.assertEqual(summary["all_time_max_hunger_npc"], "阿强")

    def test_tracks_survival_days(self):
        class FakeNPC:
            name, hunger, mood = "阿强", 50, 50
        self.mem.update(tick=2400, npcs=[FakeNPC()])
        self.assertEqual(self.mem.npc_survival_days["阿强"], 2)

    def test_tracks_collapses(self):
        class FakePressure:
            collapsed_regions = {(1, 1), (2, 2)}
        self.mem.update(tick=1200, npcs=[], pressure_map=FakePressure())
        self.assertEqual(self.mem.total_collapses, 2)
        self.assertEqual(self.mem.region_collapses[(1, 1)], 1)

    def test_avg_mood(self):
        class FakeNPC1:
            name, hunger, mood = "阿强", 50, 80
        class FakeNPC2:
            name, hunger, mood = "阿珍", 50, 20
        self.mem.update(tick=1200, npcs=[FakeNPC1(), FakeNPC2()])
        summary = self.mem.get_summary()
        self.assertEqual(summary["avg_mood_long_term"], 50.0)

    def test_get_most_dangerous_region(self):
        class FakePressure:
            collapsed_regions = {(1, 1)}
        self.mem.update(tick=1200, npcs=[], pressure_map=FakePressure())
        class FakePressure2:
            collapsed_regions = {(1, 1)}
        self.mem.update(tick=2400, npcs=[], pressure_map=FakePressure2())
        summary = self.mem.get_summary()
        self.assertIn("(1,1)", summary["most_dangerous_region"])
        self.assertEqual(summary["most_dangerous_collapses"], 2)

    def test_save_and_load(self):
        self.mem.all_time_max_hunger = 95.0
        self.mem.all_time_max_hunger_npc = "阿强"
        self.mem.total_collapses = 3
        self.mem.npc_survival_days = {"阿强": 10}
        self.mem.mood_samples = [50, 60, 70]
        self.mem.save()

        mem2 = LongTermMemory(path="/tmp/test_world_memory.json")
        self.assertEqual(mem2.all_time_max_hunger, 95.0)
        self.assertEqual(mem2.all_time_max_hunger_npc, "阿强")
        self.assertEqual(mem2.total_collapses, 3)
        self.assertEqual(mem2.npc_survival_days, {"阿强": 10})


# ═══════════════════════════════════════════════
# 工具类
# ═══════════════════════════════════════════════

class _FakeResource:
    """最小化资源管理器fake供PatternAnalyzer测试"""

    def __init__(self, total_food=30, depleted_count=0,
                 forest_count=20, depleted_forests=None):
        self._total_food = total_food
        self._depleted_count = depleted_count
        self._forest_count = forest_count
        self.depleted_forests = depleted_forests or set()

    def total_food_remaining(self):
        return self._total_food

    def forest_count(self):
        return self._forest_count


if __name__ == "__main__":
    unittest.main()
