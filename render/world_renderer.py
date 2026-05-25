"""
世界生态渲染模块 — Island Sim v1

负责：地图tile网格、depleted森林标记、蘑菇(3阶段颜色)、鱼、夜晚遮罩。
严格只读：不修改任何游戏状态。
"""

import pygame

from config import (
    COLOR_BLACK,
    COLOR_DEPLETED_FOREST,
    NIGHT_OVERLAY_ALPHA,
    MAP_HEIGHT,
    MAP_WIDTH,
    TILE_SIZE,
)


# 蘑菇颜色（按阶段）
MUSHROOM_COLORS: dict[str, tuple[int, int, int]] = {
    "fresh":  (50, 220, 50),   # 亮绿
    "old":    (120, 80, 30),   # 深棕
    "rotten": (80, 30, 80),    # 紫黑
}
MUSHROOM_RADIUS = 4

# 鱼颜色
FISH_COLOR = (180, 220, 255)   # 浅蓝/银白
FISH_RADIUS = 3


class WorldRenderer:
    """地图生态渲染器"""

    def __init__(self, font_tiny: pygame.font.Font) -> None:
        self._font_tiny = font_tiny

    def draw_ecology(
        self,
        surface: pygame.Surface,
        resource_mgr: object,
    ) -> None:
        """绘制所有生态元素：depleted森林 + 蘑菇 + 鱼"""
        self._draw_depleted(surface, resource_mgr)
        self._draw_mushrooms(surface, resource_mgr)
        self._draw_fish(surface, resource_mgr)

    # ── Depleted森林 ──

    def _draw_depleted(
        self,
        surface: pygame.Surface,
        resource_mgr: object,
    ) -> None:
        """灰绿色方块 + X标记"""
        depleted = getattr(resource_mgr, 'depleted_forests', set())
        for (fx, fy) in depleted:
            px = fx * TILE_SIZE
            py = fy * TILE_SIZE
            s = pygame.Surface((TILE_SIZE, TILE_SIZE))
            s.set_alpha(180)
            s.fill(COLOR_DEPLETED_FOREST)
            surface.blit(s, (px, py))
            cx = px + TILE_SIZE // 2
            cy = py + TILE_SIZE // 2
            pygame.draw.line(surface, (60, 60, 40),
                             (cx - 6, cy - 6), (cx + 6, cy + 6), 2)
            pygame.draw.line(surface, (60, 60, 40),
                             (cx + 6, cy - 6), (cx - 6, cy + 6), 2)

    # ── 蘑菇 ──

    def _draw_mushrooms(
        self,
        surface: pygame.Surface,
        resource_mgr: object,
    ) -> None:
        """按阶段绘制蘑菇（fresh亮绿、old深棕、rotten紫黑）"""
        mushrooms = getattr(resource_mgr, 'mushrooms', {})
        for (mx, my), info in mushrooms.items():
            stage = info.get("stage", "fresh")
            color = MUSHROOM_COLORS.get(stage, (200, 200, 200))
            cx = mx * TILE_SIZE + TILE_SIZE // 2
            cy = my * TILE_SIZE + TILE_SIZE // 2
            # 蘑菇伞形：两个半圆堆叠
            if stage == "fresh":
                r = MUSHROOM_RADIUS
            elif stage == "old":
                r = MUSHROOM_RADIUS - 1
            else:
                r = MUSHROOM_RADIUS - 1
            pygame.draw.circle(surface, color, (cx, cy), r)
            pygame.draw.circle(surface, (30, 30, 30), (cx, cy), r, 1)

    # ── 鱼 ──

    def _draw_fish(
        self,
        surface: pygame.Surface,
        resource_mgr: object,
    ) -> None:
        """浅蓝色闪点"""
        fish = getattr(resource_mgr, 'fish', {})
        for (fx, fy) in fish:
            cx = fx * TILE_SIZE + TILE_SIZE // 2
            cy = fy * TILE_SIZE + TILE_SIZE // 2
            # 鱼形：小菱形
            pts = [
                (cx + FISH_RADIUS, cy),
                (cx, cy - FISH_RADIUS),
                (cx - FISH_RADIUS, cy),
                (cx, cy + FISH_RADIUS),
            ]
            pygame.draw.polygon(surface, FISH_COLOR, pts)

    # ── 夜晚遮罩 ──

    def draw_night(
        self,
        surface: pygame.Surface,
        time_system: object,
    ) -> None:
        """夜晚时覆盖半透明黑色"""
        is_night = getattr(time_system, 'is_night', lambda: False)()
        if is_night:
            overlay = pygame.Surface((
                MAP_WIDTH * TILE_SIZE,
                MAP_HEIGHT * TILE_SIZE,
            ))
            overlay.set_alpha(NIGHT_OVERLAY_ALPHA)
            overlay.fill(COLOR_BLACK)
            surface.blit(overlay, (0, 0))
