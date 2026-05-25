"""
HUD侧栏渲染模块 — Island Sim v1

负责：右侧状态栏绘制：时间、NPC列表、世界生态面板。
严格只读：不修改任何游戏状态。
"""

import pygame

from config import (
    COLOR_SIDEBAR_BG,
    COLOR_WHITE,
    COLOR_WEAKENED_RING,
    HUD_DEPLETED_COLOR,
    HUD_FOOD_COLOR,
    HUD_MOOD_COLOR,
    HUD_WEAKENED_COLOR,
    MAP_WIDTH,
    NPC_NAME_PINYIN,
    SIDEBAR_WIDTH,
    TILE_SIZE,
    WINDOW_HEIGHT,
)
from npc.npc import NPC_COLORS


class HUDRenderer:
    """右侧侧栏HUD渲染器"""

    def __init__(self, font: pygame.font.Font, font_small: pygame.font.Font) -> None:
        self._font = font
        self._font_small = font_small
        self._pressure_map: object = None

    def set_pressure_map(self, pressure_map: object) -> None:
        self._pressure_map = pressure_map

    def draw(
        self,
        surface: pygame.Surface,
        npcs: list,
        time_system: object,
        resource_mgr: object,
    ) -> None:
        """绘制侧栏HUD：时间 + NPC列表 + 世界面板 + 压力信息"""
        sidebar_x = MAP_WIDTH * TILE_SIZE
        self._draw_background(surface, sidebar_x)
        self._draw_time(surface, sidebar_x, time_system)
        self._draw_npc_list(surface, sidebar_x, npcs)
        self._draw_world_panel(surface, sidebar_x, npcs, resource_mgr)
        self._draw_pressure_panel(surface, sidebar_x)

    def _draw_background(self, surface: pygame.Surface, sidebar_x: int) -> None:
        pygame.draw.rect(surface, COLOR_SIDEBAR_BG,
                         (sidebar_x, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT))

    def _draw_time(self, surface: pygame.Surface, sidebar_x: int,
                   time_system: object) -> None:
        time_str = time_system.get_time_string()
        time_surf = self._font.render(time_str, True, COLOR_WHITE)
        surface.blit(time_surf, (sidebar_x + 8, 8))

    def _draw_npc_list(self, surface: pygame.Surface, sidebar_x: int,
                       npcs: list) -> None:
        y = 36
        for i, npc in enumerate(npcs):
            info = npc.get_sidebar_info()
            weakened = getattr(npc, '_weakened', False)
            # 颜色小圆点（用NPC个体色便于区分身份）
            pygame.draw.circle(surface, NPC_COLORS[i],
                               (sidebar_x + 12, y + 7), 5)
            if weakened:
                pygame.draw.circle(surface, COLOR_WEAKENED_RING,
                                   (sidebar_x + 12, y + 7), 7, 2)
            # 名称（拼音） + 状态
            pinyin = NPC_NAME_PINYIN.get(info["name"], info["name"])
            state_tag = info['state']
            if weakened:
                state_tag += " W"
            line1 = self._font.render(
                f"{pinyin} [{state_tag}]", True, COLOR_WHITE)
            # 属性
            line2 = self._font_small.render(
                f"H:{info['hunger']:3d} E:{info['energy']:3d} M:{info['mood']:3d}",
                True, COLOR_WHITE)
            surface.blit(line1, (sidebar_x + 24, y))
            surface.blit(line2, (sidebar_x + 24, y + 16))
            y += 40

    def _draw_world_panel(self, surface: pygame.Surface, sidebar_x: int,
                          npcs: list, resource_mgr: object) -> None:
        if resource_mgr is None:
            return
        hud_y = WINDOW_HEIGHT - 100
        pygame.draw.line(surface, (80, 80, 80),
                         (sidebar_x + 4, hud_y - 4),
                         (sidebar_x + SIDEBAR_WIDTH - 4, hud_y - 4))
        hud_title = self._font.render("World", True, (200, 200, 200))
        surface.blit(hud_title, (sidebar_x + 8, hud_y))
        hud_y += 20

        total_food = resource_mgr.total_food_remaining()
        depleted_count = len(resource_mgr.depleted_forests)
        weakened_count = sum(1 for n in npcs if getattr(n, '_weakened', False))
        avg_mood = sum(n.mood for n in npcs) / len(npcs) if npcs else 0

        hud_lines = [
            (f"Food:{total_food:3d}", HUD_FOOD_COLOR),
            (f"Depleted:{depleted_count:2d}", HUD_DEPLETED_COLOR),
            (f"Weakened:{weakened_count:2d}", HUD_WEAKENED_COLOR),
            (f"Avg Mood:{avg_mood:3.0f}", HUD_MOOD_COLOR),
        ]
        for text, clr in hud_lines:
            line = self._font_small.render(text, True, clr)
            surface.blit(line, (sidebar_x + 12, hud_y))
            hud_y += 16

    def _draw_pressure_panel(self, surface: pygame.Surface,
                              sidebar_x: int) -> None:
        """绘制Top 3高压区域"""
        pm = self._pressure_map
        if pm is None:
            return
        top = pm.get_top_pressure(3)
        if not top:
            return

        py = WINDOW_HEIGHT - 240
        pygame.draw.line(surface, (80, 80, 80),
                         (sidebar_x + 4, py - 4),
                         (sidebar_x + SIDEBAR_WIDTH - 4, py - 4))
        title = self._font.render("--Pressure--", True, (200, 100, 100))
        surface.blit(title, (sidebar_x + 8, py))
        py += 20

        for (rx, ry), score in top:
            color = (100, 200, 100) if score < 0.3 else (
                (200, 200, 80) if score < 0.6 else (200, 80, 80))
            line = self._font_small.render(
                f"({rx},{ry}): {score:.2f}", True, color)
            surface.blit(line, (sidebar_x + 12, py))
            py += 16
