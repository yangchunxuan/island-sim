"""
NPC渲染模块 — Island Sim v1

负责：NPC彩色圆形、头顶标签（拼音+状态）、weakened指示环。
严格只读：不修改NPC状态。
"""

import pygame

from config import (
    COLOR_BLACK,
    COLOR_WEAKENED_RING,
    COLOR_WHITE,
    NPC_NAME_PINYIN,
    STATE_COLORS,
    TILE_SIZE,
)
from npc.npc import NPC_COLORS


class NPCRenderer:
    """NPC角色渲染器"""

    def __init__(self, font_tiny: pygame.font.Font) -> None:
        self._font = font_tiny

    def draw(
        self,
        surface: pygame.Surface,
        npcs: list,
    ) -> None:
        """绘制所有NPC：彩色圆形 + 头顶标签 + weakened环"""
        for i, npc in enumerate(npcs):
            cx = npc.x * TILE_SIZE + TILE_SIZE // 2
            cy = npc.y * TILE_SIZE + TILE_SIZE // 2
            radius = TILE_SIZE // 2 - 3

            weakened = bool(getattr(npc, '_weakened', False))
            state = npc.get_state()
            color = STATE_COLORS.get(state, COLOR_WHITE)

            # weakened灰色外环
            if weakened:
                pygame.draw.circle(surface, COLOR_WEAKENED_RING,
                                   (cx, cy), radius + 3, 3)

            # NPC主体
            pygame.draw.circle(surface, color, (cx, cy), radius)
            pygame.draw.circle(surface, COLOR_BLACK, (cx, cy), radius, 2)

            # 头顶标签
            self._draw_label(surface, npc, cx, cy, radius, state, weakened)

    def _draw_label(
        self,
        surface: pygame.Surface,
        npc: object,
        cx: int, cy: int,
        radius: int,
        state: str,
        weakened: bool,
    ) -> None:
        """绘制NPC头顶拼音+状态标签"""
        pinyin = NPC_NAME_PINYIN.get(npc.name, npc.name)
        label_state = state
        if weakened:
            label_state += " WEAK"
        name_surf = self._font.render(pinyin, True, COLOR_BLACK)
        state_surf = self._font.render(label_state, True, COLOR_BLACK)

        nw = name_surf.get_width()
        sw = state_surf.get_width()
        label_w = max(nw, sw) + 4
        label_h = self._font.get_height() * 2 + 4

        lx = cx - label_w // 2
        ly = cy - radius - label_h

        pygame.draw.rect(surface, (255, 255, 255), (lx, ly, label_w, label_h))
        pygame.draw.rect(surface, COLOR_BLACK, (lx, ly, label_w, label_h), 1)
        surface.blit(name_surf, (cx - nw // 2, ly + 2))
        surface.blit(state_surf, (cx - sw // 2, ly + 2 + self._font.get_height()))
