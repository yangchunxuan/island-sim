"""
回放验证器测试 — Island Sim v1

验证 replay_validator 的事件-状态一致性检查。
"""

import unittest


class MockNPC:
    def __init__(self, name="TestNPC", hunger=50, x=5, y=5,
                 weakened=False, state="IDLE"):
        self.name = name
        self.hunger = hunger
        self.x = x
        self.y = y
        self._weakened = weakened
        self._state = state

    def get_state(self):
        return self._state


class MockResourceMgr:
    def __init__(self):
        self.mushrooms = {(5, 6): 1, (7, 5): 2}
        self.fish = {(4, 4): 1, (5, 5): 1}
        self.depleted_forests = {(1, 1), (2, 3), (14, 8)}


class TestReplayValidator(unittest.TestCase):
    """测试 ReplayValidator 核心功能"""

    @classmethod
    def setUpClass(cls):
        from observer.replay_validator import ReplayValidator
        cls.ValidatorClass = ReplayValidator

    def test_verify_eat_event_hunger_check(self):
        validator = self.ValidatorClass()
        event = {
            "event_type": "NPC_EAT",
            "npc": "阿强",
            "position": (5, 5),
            "details": {"hunger_drop": 30},
        }
        npcs = [MockNPC(name="阿强", hunger=40, x=5, y=5)]
        result = validator.verify_event(event, npcs, MockResourceMgr(), 100)
        self.assertIsInstance(result, dict)
        self.assertIn("valid", result)
        self.assertIn("checks", result)

    def test_verify_eat_npc_not_found(self):
        validator = self.ValidatorClass()
        event = {
            "event_type": "NPC_EAT",
            "npc": "NotFound",
            "position": (5, 5),
        }
        result = validator.verify_event(event, [], MockResourceMgr(), 100)
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["issues"]), 0)

    def test_verify_weakened_high_hunger(self):
        validator = self.ValidatorClass()
        event = {
            "event_type": "NPC_ENTER_WEAKENED",
            "npc": "阿强",
            "position": (5, 5),
            "details": {"hunger": 85},
        }
        npcs = [MockNPC(name="阿强", hunger=85, weakened=True)]
        result = validator.verify_event(event, npcs, MockResourceMgr(), 100)
        self.assertIn("checks", result)

    def test_verify_weakened_low_hunger_flags_issue(self):
        validator = self.ValidatorClass()
        event = {
            "event_type": "NPC_ENTER_WEAKENED",
            "npc": "阿强",
            "position": (5, 5),
            "details": {"hunger": 85},
        }
        # hunger < 80 但事件说是 weakened → 问题
        npcs = [MockNPC(name="阿强", hunger=50, weakened=True)]
        result = validator.verify_event(event, npcs, MockResourceMgr(), 100)
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["issues"]), 0)

    def test_verify_sleep_matching_state(self):
        validator = self.ValidatorClass()
        event = {
            "event_type": "NPC_SLEEP",
            "npc": "小美",
            "position": (3, 3),
        }
        npcs = [MockNPC(name="小美", x=3, y=3, state="SLEEP")]
        result = validator.verify_event(event, npcs, MockResourceMgr(), 200)
        self.assertTrue(result["valid"])

    def test_verify_sleep_wrong_state(self):
        validator = self.ValidatorClass()
        event = {
            "event_type": "NPC_SLEEP",
            "npc": "小美",
            "position": (3, 3),
        }
        npcs = [MockNPC(name="小美", x=3, y=3, state="WALK")]
        result = validator.verify_event(event, npcs, MockResourceMgr(), 200)
        self.assertFalse(result["valid"])

    def test_verify_movement_position_check(self):
        validator = self.ValidatorClass()
        event = {
            "event_type": "NPC_MOVE_REGION",
            "npc": "大壮",
            "position": (10, 8),
            "details": {"from": "西北森林", "to": "东北海岸"},
        }
        npcs = [MockNPC(name="大壮", x=10, y=8)]
        result = validator.verify_event(event, npcs, MockResourceMgr(), 300)
        self.assertTrue(result["valid"])

    def test_verify_movement_wrong_position(self):
        validator = self.ValidatorClass()
        event = {
            "event_type": "NPC_MOVE_REGION",
            "npc": "大壮",
            "position": (10, 8),
            "details": {"from": "西北森林", "to": "东北海岸"},
        }
        npcs = [MockNPC(name="大壮", x=2, y=2)]
        result = validator.verify_event(event, npcs, MockResourceMgr(), 300)
        self.assertFalse(result["valid"])

    def test_verify_resource_depleted(self):
        validator = self.ValidatorClass()
        event = {
            "event_type": "RESOURCE_DEPLETED",
            "position": (14, 8),
            "details": {"type": "forest"},
        }
        result = validator.verify_event(event, [], MockResourceMgr(), 400)
        # (14,8) is in depleted_forests
        self.assertTrue(result["valid"])

    def test_verify_resource_not_depleted(self):
        validator = self.ValidatorClass()
        event = {
            "event_type": "RESOURCE_DEPLETED",
            "position": (5, 5),
            "details": {"type": "forest"},
        }
        result = validator.verify_event(event, [], MockResourceMgr(), 400)
        # (5,5) is NOT in depleted_forests (mushroom there but not depleted)
        self.assertFalse(result["valid"])

    def test_verify_forest_recovered(self):
        validator = self.ValidatorClass()
        event = {
            "event_type": "FOREST_RECOVERED",
            "position": (1, 1),
            "details": {},
        }
        result = validator.verify_event(event, [], MockResourceMgr(), 500)
        # (1,1) IS in depleted_forests, so NOT recovered
        self.assertFalse(result["valid"])

    def test_batch_verify_counts(self):
        validator = self.ValidatorClass()
        events = [
            {"event_type": "NPC_SLEEP", "npc": "阿强",
             "position": (5, 5)},
            {"event_type": "NPC_MOVE_REGION", "npc": "NotFound",
             "position": (5, 5)},
        ]
        npcs = [MockNPC(name="阿强", state="SLEEP")]
        result = validator.batch_verify(events, npcs, MockResourceMgr(), 100)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["passed"], 1)
        self.assertEqual(result["failed"], 1)

    def test_unknown_event_type_does_not_crash(self):
        validator = self.ValidatorClass()
        event = {
            "event_type": "MUSHROOM_SPAWN",
            "position": (5, 5),
            "details": {},
        }
        result = validator.verify_event(event, [], MockResourceMgr(), 100)
        self.assertIsInstance(result, dict)
        self.assertTrue(result["valid"])  # unknown events pass by default


if __name__ == "__main__":
    unittest.main()
