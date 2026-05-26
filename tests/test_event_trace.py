"""
事件追踪测试 — Island Sim v1

验证 event_trace 功能：注册/查找/反向追踪。
"""

import unittest


class TestEventTrace(unittest.TestCase):
    """测试 EventTrace 核心功能"""

    @classmethod
    def setUpClass(cls):
        from observer.event_trace import EventTrace
        cls.TraceClass = EventTrace

    def test_register_returns_id(self):
        trace = self.TraceClass()
        eid = trace.register({"event_type": "NPC_EAT", "tick": 100})
        self.assertGreaterEqual(eid, 0)

    def test_register_increments_id(self):
        trace = self.TraceClass()
        eid1 = trace.register({"event_type": "NPC_EAT", "tick": 100})
        eid2 = trace.register({"event_type": "NPC_SLEEP", "tick": 200})
        self.assertEqual(eid2, eid1 + 1)

    def test_lookup_returns_event(self):
        trace = self.TraceClass()
        event = {"event_type": "NPC_EAT", "tick": 100, "npc": "阿强"}
        eid = trace.register(event)
        result = trace.lookup(eid)
        self.assertIsNotNone(result)
        self.assertEqual(result["event_type"], "NPC_EAT")
        self.assertEqual(result["npc"], "阿强")

    def test_lookup_nonexistent_returns_none(self):
        trace = self.TraceClass()
        self.assertIsNone(trace.lookup(999))

    def test_find_by_type(self):
        trace = self.TraceClass()
        trace.register({"event_type": "NPC_EAT", "tick": 100})
        trace.register({"event_type": "NPC_SLEEP", "tick": 200})
        trace.register({"event_type": "NPC_EAT", "tick": 300})
        results = trace.find_by_type("NPC_EAT")
        self.assertEqual(len(results), 2)

    def test_find_by_tick(self):
        trace = self.TraceClass()
        trace.register({"event_type": "NPC_EAT", "tick": 100})
        trace.register({"event_type": "NPC_SLEEP", "tick": 100})
        trace.register({"event_type": "NPC_WALK", "tick": 200})
        results = trace.find_by_tick(100)
        self.assertEqual(len(results), 2)

    def test_count(self):
        trace = self.TraceClass()
        self.assertEqual(trace.count, 0)
        trace.register({"event_type": "NPC_EAT", "tick": 100})
        self.assertEqual(trace.count, 1)
        trace.register({"event_type": "NPC_SLEEP", "tick": 200})
        self.assertEqual(trace.count, 2)

    def test_get_last_event_id(self):
        trace = self.TraceClass()
        self.assertEqual(trace.get_last_event_id(), -1)
        eid = trace.register({"event_type": "NPC_EAT", "tick": 100})
        self.assertEqual(trace.get_last_event_id(), eid)

    def test_registered_event_has_trace_id(self):
        trace = self.TraceClass()
        eid = trace.register({"event_type": "NPC_EAT", "tick": 100})
        event_copy = trace.lookup(eid)
        self.assertIn("event_id", event_copy)
        self.assertEqual(event_copy["event_id"], eid)

    def test_trace_preserves_details(self):
        trace = self.TraceClass()
        event = {
            "event_type": "NPC_MOVE_REGION",
            "tick": 150,
            "npc": "大壮",
            "position": (10, 5),
            "details": {"from": "西北森林", "to": "东北海岸"},
        }
        eid = trace.register(event)
        stored = trace.lookup(eid)
        self.assertEqual(stored["position"], (10, 5))
        self.assertEqual(stored["details"]["to"], "东北海岸")


class TestTraceIntegration(unittest.TestCase):
    """验证 event_trace 可从 WorldObserver 访问"""

    def test_observer_has_event_trace(self):
        from observer.world_observer import WorldObserver
        observer = WorldObserver()
        self.assertTrue(hasattr(observer, "event_trace"))
        from observer.event_trace import EventTrace
        self.assertIsInstance(observer.event_trace, EventTrace)

    def test_observer_has_evidence_system(self):
        from observer.world_observer import WorldObserver
        observer = WorldObserver()
        self.assertTrue(hasattr(observer, "evidence_system"))


if __name__ == "__main__":
    unittest.main()
