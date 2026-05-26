"""
证据链系统测试 — Island Sim v1

验证 evidence_system 证据收集/存储/置信度计算。
"""

import unittest


class MockNPC:
    def __init__(self, name="TestNPC", hunger=50, energy=50, x=5, y=5,
                 weakened=False, state="IDLE"):
        self.name = name
        self.hunger = hunger
        self.energy = energy
        self.x = x
        self.y = y
        self._weakened = weakened
        self.state = state

    def get_state(self):
        return self.state


class MockResourceMgr:
    def __init__(self, total_food=100):
        self._mushrooms = {(5, 6): 1, (7, 5): 2}
        self._fish = {(4, 4): 1, (5, 5): 1}
        self._depleted_forests = {(1, 1), (2, 3)}

    def total_food_remaining(self):
        return len(self._mushrooms) + len(self._fish)

    @property
    def mushrooms(self):
        return self._mushrooms

    @property
    def fish(self):
        return self._fish

    @property
    def depleted_forests(self):
        return self._depleted_forests


class TestEvidenceSystem(unittest.TestCase):
    """测试 EvidenceSystem"""

    @classmethod
    def setUpClass(cls):
        from observer.evidence_system import EvidenceSystem
        cls.EvidenceClass = EvidenceSystem

    def test_collect_npc_evidence_contains_hunger(self):
        evidence = self.EvidenceClass()
        npc = MockNPC(hunger=85)
        result = evidence.collect_npc_evidence(npc, MockResourceMgr())
        self.assertIn("hunger", result)
        self.assertEqual(result["hunger"], 85)

    def test_collect_npc_evidence_contains_position(self):
        evidence = self.EvidenceClass()
        npc = MockNPC(x=14, y=8)
        result = evidence.collect_npc_evidence(npc, MockResourceMgr())
        self.assertEqual(result["position"], (14, 8))

    def test_collect_npc_evidence_contains_nearby_food(self):
        evidence = self.EvidenceClass()
        npc = MockNPC(x=5, y=5, name="阿强")
        result = evidence.collect_npc_evidence(npc, MockResourceMgr())
        # mushrooms at (5,6), (7,5); fish at (4,4), (5,5)
        # All within distance 3 of (5,5)
        self.assertIsNotNone(result.get("nearby_food"))
        self.assertGreaterEqual(result["nearby_food"], 2)

    def test_collect_resource_evidence(self):
        evidence = self.EvidenceClass()
        result = evidence.collect_resource_evidence(5, 5, MockResourceMgr())
        self.assertIn("total_food", result)
        self.assertIn("depleted_forests", result)

    def test_store_and_get_evidence(self):
        evidence = self.EvidenceClass()
        ev = {"hunger": 90, "nearby_food": 0}
        evidence.store(42, ev)
        result = evidence.get_evidence(42)
        self.assertEqual(result["hunger"], 90)

    def test_get_evidence_nonexistent(self):
        evidence = self.EvidenceClass()
        result = evidence.get_evidence(999)
        self.assertEqual(result, {})

    def test_confidence_direct_event(self):
        evidence = self.EvidenceClass()
        conf = evidence.compute_confidence(
            "NPC_EAT", {"hunger": 50},
        )
        self.assertEqual(conf, 1.0)

    def test_confidence_weakened_high_hunger(self):
        evidence = self.EvidenceClass()
        conf = evidence.compute_confidence(
            "NPC_ENTER_WEAKENED", {"hunger": 85},
        )
        self.assertEqual(conf, 1.0)

    def test_confidence_weakened_medium_hunger(self):
        evidence = self.EvidenceClass()
        conf = evidence.compute_confidence(
            "NPC_ENTER_WEAKENED", {"hunger": 65},
        )
        self.assertEqual(conf, 0.9)

    def test_confidence_weakened_low_hunger(self):
        evidence = self.EvidenceClass()
        conf = evidence.compute_confidence(
            "NPC_ENTER_WEAKENED", {"hunger": 40},
        )
        self.assertEqual(conf, 0.75)

    def test_confidence_resource_depleted(self):
        evidence = self.EvidenceClass()
        conf = evidence.compute_confidence(
            "RESOURCE_DEPLETED", {"depleted_forests": 1},
        )
        self.assertGreaterEqual(conf, 0.5)

    def test_confidence_region_collapse_high_pressure(self):
        evidence = self.EvidenceClass()
        conf = evidence.compute_confidence(
            "REGION_COLLAPSE", {"region_pressure": 0.85},
        )
        self.assertEqual(conf, 1.0)

    def test_confidence_generic_low(self):
        evidence = self.EvidenceClass()
        conf = evidence.compute_confidence(
            "UNKNOWN_TYPE", {},
        )
        self.assertEqual(conf, 0.7)

    def test_confidence_not_below_threshold(self):
        """所有置信度应 >= 0.5"""
        evidence = self.EvidenceClass()
        for et in ("NPC_EAT", "NPC_SLEEP", "NPC_MOVE_REGION",
                   "NPC_ENTER_WEAKENED", "RESOURCE_DEPLETED",
                   "REGION_COLLAPSE", "REGION_RECOVERY",
                   "MUSHROOM_SPAWN", "FISH_SPAWN", "FOREST_RECOVERED"):
            conf = evidence.compute_confidence(et, {})
            self.assertGreaterEqual(conf, 0.5, f"{et} confidence too low")

    def test_evidence_preview(self):
        evidence = self.EvidenceClass()
        evidence.store(42, {"hunger": 85, "nearby_food": 0})
        preview = evidence.get_evidence_preview(42)
        self.assertIn("hunger=85", preview)

    def test_evidence_preview_empty(self):
        evidence = self.EvidenceClass()
        preview = evidence.get_evidence_preview(999)
        self.assertEqual(preview, "")


class TestEvidenceIntegration(unittest.TestCase):
    """验证 evidence_system 可从 WorldObserver 访问"""

    def test_observer_has_evidence_system(self):
        from observer.world_observer import WorldObserver
        observer = WorldObserver()
        self.assertTrue(hasattr(observer, "evidence_system"))
        from observer.evidence_system import EvidenceSystem
        self.assertIsInstance(observer.evidence_system, EvidenceSystem)


if __name__ == "__main__":
    unittest.main()
