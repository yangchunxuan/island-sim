"""
渲染模块统一入口 — Island Sim v1

Renderer类协调所有子渲染器，提供统一的draw()接口。
严格只读：读取状态 → 绘制，禁止修改任何游戏状态。
"""

import pygame

from config import (
    MAP_HEIGHT,
    MAP_WIDTH,
    OVERLAY_NONE,
    SIDEBAR_WIDTH,
    TILE_SIZE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from render.world_renderer import WorldRenderer
from render.npc_renderer import NPCRenderer
from render.debug_renderer import DebugRenderer
from render.hud_renderer import HUDRenderer


class Renderer:
    """渲染协调器：绑定游戏对象，每帧按序绘制"""

    def __init__(self) -> None:
        self._screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("孤岛世界 v1")
        self._font = pygame.font.Font(None, 18)
        self._font_small = pygame.font.Font(None, 14)
        self._font_tiny = pygame.font.Font(None, 12)

        self._world = WorldRenderer(self._font_tiny)
        self._npc = NPCRenderer(self._font_tiny)
        self._debug = DebugRenderer(self._font_small)
        self._hud = HUDRenderer(self._font, self._font_small)

    def set_game_objects(self, game_map, resource_mgr, time_system,
                         npcs) -> None:
        """绑定游戏状态引用"""
        self._game_map = game_map
        self._resource_mgr = resource_mgr
        self._time_system = time_system
        self._npcs = npcs

    def set_pressure_map(self, pressure_map: object) -> None:
        """注入区域压力图（传递给HUD和Debug层）"""
        self._hud.set_pressure_map(pressure_map)
        self._debug.set_heatmap_data(pressure_map, self._resource_mgr)

    def draw(self, overlay_mode: int = OVERLAY_NONE) -> None:
        """全帧渲染，严格按固定顺序"""
        surface = self._screen

        # 1. 地图
        self._game_map.draw(surface)

        # 2. 资源生态（depleted森林、蘑菇、鱼）
        if self._resource_mgr is not None:
            self._world.draw_ecology(surface, self._resource_mgr)

        # 3. NPC
        self._npc.draw(surface, self._npcs)

        # 4. Debug overlay
        if overlay_mode != OVERLAY_NONE:
            self._debug.draw(surface, self._npcs, self._game_map,
                             overlay_mode)

        # 5. 夜晚遮罩
        if self._time_system is not None:
            self._world.draw_night(surface, self._time_system)

        # 6. 侧栏HUD
        self._hud.draw(surface, self._npcs, self._time_system,
                       self._resource_mgr)

        pygame.display.flip()

    @property
    def screen(self):
        return self._screen
