"""
渲染模块测试 — Island Sim v1

验证渲染器创建、draw()调用不崩溃、只读原则。
"""

import os
import unittest

import pygame

from config import OVERLAY_NONE, OVERLAY_TILE, OVERLAY_STATS, OVERLAY_PATH
from render import Renderer


class FakeNPC:
    """最小化NPC fake，避免pygame Mock的__getattr__问题"""

    def __init__(self) -> None:
        self.x = 5
        self.y = 5
        self.hunger = 50
        self.energy = 80
        self.mood = 60
        self.name = "阿强"
        self._weakened = False
        self._path: list = []
        self.target_x: int | None = None
        self.target_y: int | None = None

    def get_state(self) -> str:
        return "IDLE"

    def get_sidebar_info(self) -> dict:
        return {
            "name": self.name,
            "hunger": int(self.hunger),
            "energy": int(self.energy),
            "mood": int(self.mood),
            "state": self.get_state(),
        }


class FakeGameMap:
    def draw(self, surface: pygame.Surface) -> None:
        pass

    def get_tile(self, x: int, y: int) -> int:
        return 2  # GRASS


class FakeResourceManager:
    def __init__(self) -> None:
        self.depleted_forests: set = set()
        self.mushrooms: dict = {}
        self.fish: dict = {}

    def total_food_remaining(self) -> int:
        return 0


class FakeTimeSystem:
    def get_time_string(self) -> str:
        return "Day 1 12:00"

    def is_night(self) -> bool:
        return False


class TestRendererCreate(unittest.TestCase):
    """渲染器创建测试"""

    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_create_renderer(self):
        r = Renderer()
        self.assertIsNotNone(r)

    def test_screen_property(self):
        r = Renderer()
        self.assertIsNotNone(r.screen)

    def test_set_game_objects(self):
        r = Renderer()
        r.set_game_objects(FakeGameMap(), FakeResourceManager(),
                           FakeTimeSystem(), [])
        # No exception = pass


class TestRendererDraw(unittest.TestCase):
    """draw()不崩溃测试"""

    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.renderer = Renderer()
        self.renderer.set_game_objects(
            FakeGameMap(), FakeResourceManager(),
            FakeTimeSystem(), [])

    def test_draw_no_overlay(self):
        self.renderer.draw(OVERLAY_NONE)

    def test_draw_tile_overlay(self):
        self.renderer.draw(OVERLAY_TILE)

    def test_draw_stats_overlay(self):
        self.renderer.draw(OVERLAY_STATS)

    def test_draw_path_overlay(self):
        self.renderer.draw(OVERLAY_PATH)

    def test_draw_with_npcs(self):
        r = Renderer()
        r.set_game_objects(FakeGameMap(), FakeResourceManager(),
                           FakeTimeSystem(), [FakeNPC(), FakeNPC()])
        r.draw(OVERLAY_NONE)
        r.draw(OVERLAY_TILE)
        r.draw(OVERLAY_STATS)
        r.draw(OVERLAY_PATH)

    def test_draw_night(self):
        class NightTime:
            def get_time_string(self): return "Day 1 00:00"
            def is_night(self): return True

        r = Renderer()
        r.set_game_objects(FakeGameMap(), FakeResourceManager(),
                           NightTime(), [FakeNPC()])
        r.draw(OVERLAY_NONE)

    def test_draw_resource_none(self):
        r = Renderer()
        r.set_game_objects(FakeGameMap(), None, FakeTimeSystem(), [])
        r.draw(OVERLAY_NONE)

    def test_draw_mushrooms_and_fish(self):
        rm = FakeResourceManager()
        rm.mushrooms = {(5, 5): {"age": 20, "stage": "fresh"}}
        rm.fish = {(10, 10): {"age": 5}}
        r = Renderer()
        r.set_game_objects(FakeGameMap(), rm, FakeTimeSystem(), [FakeNPC()])
        r.draw(OVERLAY_NONE)

    def test_draw_depleted_forest(self):
        rm = FakeResourceManager()
        rm.depleted_forests = {(3, 3)}
        r = Renderer()
        r.set_game_objects(FakeGameMap(), rm, FakeTimeSystem(), [])
        r.draw(OVERLAY_NONE)


class TestRendererReadOnly(unittest.TestCase):
    """验证渲染器不修改游戏状态"""

    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_npc_state_unchanged_after_draw(self):
        r = Renderer()
        npc = FakeNPC()
        orig_x = npc.x
        orig_y = npc.y
        orig_hunger = npc.hunger
        orig_energy = npc.energy

        r.set_game_objects(FakeGameMap(), FakeResourceManager(),
                           FakeTimeSystem(), [npc])
        for _ in range(10):
            r.draw(OVERLAY_NONE)
            r.draw(OVERLAY_TILE)
            r.draw(OVERLAY_PATH)

        self.assertEqual(npc.x, orig_x)
        self.assertEqual(npc.y, orig_y)
        self.assertEqual(npc.hunger, orig_hunger)
        self.assertEqual(npc.energy, orig_energy)

    def test_resource_unchanged_after_draw(self):
        r = Renderer()
        rm = FakeResourceManager()

        r.set_game_objects(FakeGameMap(), rm, FakeTimeSystem(), [])
        for _ in range(5):
            r.draw(OVERLAY_NONE)

        self.assertEqual(rm.total_food_remaining(), 0)
        self.assertEqual(len(rm.depleted_forests), 0)


if __name__ == "__main__":
    unittest.main()
