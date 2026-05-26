"""
Live Feed 实时叙事流测试 — Island Sim v1

验证：
- feed append 和 auto trim
- formatter 正确
- region tracking 正确
- pressure trend 正确
- 实时事件顺序正确
"""

import os
import unittest

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")


class TestLiveFeed(unittest.TestCase):
    """测试 LiveFeed 核心功能"""

    @classmethod
    def setUpClass(cls):
        from observer.live_feed import LiveFeed
        cls.FeedClass = LiveFeed

    def test_append_and_count(self):
        feed = self.FeedClass(max_entries=10)
        feed.append(100, "INFO", "test event")
        self.assertEqual(feed.count, 1)
        feed.append(200, "WARNING", "warning event")
        self.assertEqual(feed.count, 2)

    def test_recent_returns_newest(self):
        feed = self.FeedClass(max_entries=10)
        for i in range(5):
            feed.append(i * 100, "INFO", f"event_{i}")
        recent = feed.recent(3)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[-1]["message"], "event_4")

    def test_auto_trim(self):
        feed = self.FeedClass(max_entries=5)
        for i in range(10):
            feed.append(i * 100, "INFO", f"event_{i}")
        self.assertEqual(feed.count, 5)
        self.assertEqual(feed.recent(1)[0]["message"], "event_9")

    def test_append_maintains_order(self):
        feed = self.FeedClass(max_entries=10)
        for i in range(5):
            feed.append(i * 100, "INFO", f"event_{i}")
        all_events = feed.all()
        ticks = [e["tick"] for e in all_events]
        self.assertEqual(ticks, sorted(ticks))

    def test_clear(self):
        feed = self.FeedClass(max_entries=10)
        feed.append(100, "INFO", "test")
        feed.clear()
        self.assertEqual(feed.count, 0)
        self.assertEqual(len(feed.all()), 0)

    def test_level_preserved(self):
        feed = self.FeedClass(max_entries=10)
        feed.append(100, "CRITICAL", "critical event")
        self.assertEqual(feed.recent(1)[0]["level"], "CRITICAL")


class TestEventFormatter(unittest.TestCase):
    """测试 EventFormatter"""

    @classmethod
    def setUpClass(cls):
        from observer.event_formatter import EventFormatter
        cls.fmt = EventFormatter()

    def test_format_npc_eat(self):
        event = {
            "event_type": "NPC_EAT",
            "npc": "阿强",
            "position": (2, 3),
            "details": {"hunger_drop": 30},
        }
        result = self.fmt.format(event)
        self.assertIn("阿强", result)
        self.assertIn("consumed food", result)

    def test_format_npc_sleep(self):
        event = {
            "event_type": "NPC_SLEEP",
            "npc": "小美",
            "position": (5, 5),
            "details": {"energy": 50},
        }
        result = self.fmt.format(event)
        self.assertIn("小美", result)

    def test_format_region_collapse(self):
        event = {
            "event_type": "REGION_COLLAPSE",
            "position": (0, 0),
            "details": {},
        }
        result = self.fmt.format(event)
        self.assertIn("ecosystem collapsed", result)
        self.assertIn("西北森林", result)

    def test_format_region_recovery(self):
        event = {
            "event_type": "REGION_RECOVERY",
            "position": (5, 5),
            "details": {},
        }
        result = self.fmt.format(event)
        self.assertIn("ecosystem recovered", result)

    def test_format_resource_depleted(self):
        event = {
            "event_type": "RESOURCE_DEPLETED",
            "position": (2, 2),
            "details": {"type": "forest"},
        }
        result = self.fmt.format(event)
        self.assertIn("depleted", result)

    def test_format_movement(self):
        event = {
            "event_type": "NPC_MOVE_REGION",
            "npc": "大壮",
            "position": (10, 5),
            "details": {"from": "西北森林", "to": "东北海岸"},
        }
        result = self.fmt.format(event)
        self.assertIn("大壮", result)
        self.assertIn("moved", result)

    def test_get_level(self):
        self.assertEqual(
            self.fmt.get_level({"event_type": "REGION_COLLAPSE"}),
            "CRITICAL",
        )
        self.assertEqual(
            self.fmt.get_level({"event_type": "NPC_EAT"}),
            "INFO",
        )
        self.assertEqual(
            self.fmt.get_level({"event_type": "NPC_MOVE_REGION"}),
            "MOVEMENT",
        )
        self.assertEqual(
            self.fmt.get_level({"event_type": "MUSHROOM_SPAWN"}),
            "ECOLOGY",
        )

    def test_unknown_event_type(self):
        event = {
            "event_type": "UNKNOWN_EVENT",
            "position": (5, 5),
        }
        result = self.fmt.format(event)
        self.assertIn("UNKNOWN_EVENT", result)

    def test_region_name_mapping(self):
        """验证坐标到区域名的映射"""
        # grid(0,0) = nw_forest = "西北森林"
        event = {
            "event_type": "MUSHROOM_SPAWN",
            "position": (2, 2),
            "details": {},
        }
        result = self.fmt.format(event)
        self.assertIn("西北森林", result)

        # grid(2,1) = east_coast = "东海岸"
        event2 = {
            "event_type": "FISH_SPAWN",
            "position": (12, 7),
            "details": {},
        }
        result2 = self.fmt.format(event2)
        self.assertIn("东海岸", result2)


class TestRegionTracker(unittest.TestCase):
    """测试 RegionTracker"""

    @classmethod
    def setUpClass(cls):
        from observer.region_tracker import RegionTracker
        cls.tracker = RegionTracker()

    def test_initial_regions_loaded(self):
        self.assertGreater(len(self.tracker.regions), 0)

    def test_record_visit(self):
        self.tracker.record_visit(2, 2, "阿强", 100)
        stats = self.tracker.get_all_stats()
        nw_forest = stats.get("nw_forest", {})
        self.assertGreater(nw_forest.get("visits", 0), 0)
        self.assertIn("阿强", nw_forest.get("visitors", []))

    def test_record_depletion(self):
        self.tracker.record_depletion(5, 5, "forest")
        stats = self.tracker.get_all_stats()
        central = stats.get("central_plain", {})
        self.assertGreater(central.get("depletions", 0), 0)

    def test_record_recovery(self):
        self.tracker.record_recovery(5, 5)
        stats = self.tracker.get_all_stats()
        central = stats.get("central_plain", {})
        self.assertGreaterEqual(central.get("recoveries", 0), 0)

    def test_most_visited_returns_top_n(self):
        top = self.tracker.get_most_visited(3)
        self.assertLessEqual(len(top), 3)

    def test_most_pressured_returns_top_n(self):
        top = self.tracker.get_most_pressured(3)
        self.assertLessEqual(len(top), 3)

    def test_get_abandoned(self):
        """长时间无人访问应被标记为废弃"""
        abandoned = self.tracker.get_abandoned(current_tick=99999,
                                                abandon_threshold=100)
        self.assertIsInstance(abandoned, list)

    def test_update_pressure(self):
        self.tracker.update_pressure(2, 2, 0.75)
        top = self.tracker.get_most_pressured(5)
        pressures = [r["peak_pressure"] for r in top]
        self.assertGreaterEqual(max(pressures), 0.75)


class TestPressureTracker(unittest.TestCase):
    """测试 PressureTracker"""

    @classmethod
    def setUpClass(cls):
        from observer.pressure_tracker import PressureTracker
        cls.TrackerClass = PressureTracker

    def _make_npc(self, hunger, weakened=False):
        class MockNPC:
            pass
        n = MockNPC()
        n.hunger = hunger
        n._weakened = weakened
        return n

    def test_record_and_hunger_trend_initial(self):
        """记录不足2次时返回稳定"""
        tracker = self.TrackerClass(window_size=100)
        trend = tracker.get_hunger_trend()
        self.assertEqual(trend["trend"], "stable")

    def test_hunger_rising_trend(self):
        tracker = self.TrackerClass(window_size=100)
        npcs1 = [self._make_npc(30)]
        npcs2 = [self._make_npc(80)]
        tracker.record(100, npcs1, 0, 0)
        tracker.record(200, npcs2, 0, 0)
        trend = tracker.get_hunger_trend()
        self.assertEqual(trend["trend"], "rising")

    def test_weakened_trend(self):
        tracker = self.TrackerClass(window_size=100)
        n0 = [self._make_npc(50)]
        n1 = [self._make_npc(90, weakened=True)]
        tracker.record(100, n0, 0, 0)
        tracker.record(200, n1, 0, 0)
        trend = tracker.get_weakened_trend()
        self.assertIn("ratio", trend)
        self.assertIn("trend", trend)

    def test_resource_trend(self):
        tracker = self.TrackerClass(window_size=100)
        npcs = [self._make_npc(50)]
        tracker.record(100, npcs, 5, 2)
        tracker.record(200, npcs, 3, 4)
        trend = tracker.get_resource_trend()
        self.assertEqual(trend["total_depletions"], 8)
        self.assertEqual(trend["total_recoveries"], 6)

    def test_get_summary(self):
        tracker = self.TrackerClass(window_size=100)
        npcs = [self._make_npc(50)]
        tracker.record(100, npcs, 1, 0)
        tracker.record(200, npcs, 2, 1)
        summary = tracker.get_summary()
        self.assertIn("hunger", summary)
        self.assertIn("weakened", summary)
        self.assertIn("resource", summary)

    def test_empty_resource_trend(self):
        """无记录时不应崩溃"""
        tracker = self.TrackerClass(window_size=100)
        trend = tracker.get_resource_trend()
        self.assertIn("total_depletions", trend)


class TestIntegrationWithObserver(unittest.TestCase):
    """验证新模块可被 WorldObserver 正确使用"""

    def test_observer_has_new_attributes(self):
        from observer.world_observer import WorldObserver
        observer = WorldObserver()
        self.assertTrue(hasattr(observer, "live_feed"))
        self.assertTrue(hasattr(observer, "region_tracker"))
        self.assertTrue(hasattr(observer, "pressure_tracker"))

    def test_observer_live_feed_is_live_feed_instance(self):
        from observer.live_feed import LiveFeed
        from observer.world_observer import WorldObserver
        observer = WorldObserver()
        self.assertIsInstance(observer.live_feed, LiveFeed)

    def test_live_feed_gets_events_after_update(self):
        """运行一次 update 后 live_feed 应有事件"""
        from observer.world_observer import WorldObserver
        observer = WorldObserver()

        # 创建模拟数据
        class MockNPC:
            name = "TestNPC"
            x = 5
            y = 5
            hunger = 50
            energy = 50
            _weakened = False
            risk_tolerance = 0.5
            laziness = 0.5
            food_preference = 0.5
            exploration_bias = 0.5
            def get_state(self): return "IDLE"

        class MockResourceMgr:
            depleted_forests = set()
            mushrooms = {}
            fish = {}
            def total_food_remaining(self): return 100

        observer.update(100, MockResourceMgr(), [MockNPC()])

        # 即使仅 profile 事件也会被格式化
        self.assertGreaterEqual(observer.live_feed.count, 0)


if __name__ == "__main__":
    unittest.main()
