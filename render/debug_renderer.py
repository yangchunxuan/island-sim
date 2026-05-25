"""
调试覆盖层渲染模块 — Island Sim v1

负责：F1网格文字、F2属性数值、F3路径线段。
严格只读：不修改任何游戏状态。
"""

import pygame

from config import (
    COLOR_BLACK,
    HEATMAP_ALPHA,
    HEATMAP_COLORS,
    MAP_HEIGHT,
    MAP_WIDTH,
    OVERLAY_TILE,
    OVERLAY_STATS,
    OVERLAY_PATH,
    OVERLAY_HEATMAP,
    TILE_LABELS,
    TILE_SIZE,
)


class DebugRenderer:
    """调试覆盖层渲染器（F1-F4）"""

    def __init__(self, font_small: pygame.font.Font) -> None:
        self._font = font_small

    def set_heatmap_data(
        self, pressure_map: object, resource_mgr: object,
    ) -> None:
        """注入热力图数据"""
        self._pressure_map = pressure_map
        self._resource_mgr = resource_mgr

    def draw(
        self,
        surface: pygame.Surface,
        npcs: list,
        game_map: object,
        mode: int,
    ) -> None:
        """按当前模式绘制"""
        if mode == OVERLAY_TILE:
            self._draw_tile_grid(surface, game_map)
        elif mode == OVERLAY_STATS:
            self._draw_npc_stats(surface, npcs)
        elif mode == OVERLAY_PATH:
            self._draw_paths(surface, npcs)
        elif mode == OVERLAY_HEATMAP:
            self._draw_heatmap(surface)

    def _get_heat_color(self, value: float) -> tuple[int, int, int]:
        """压力值(0~1)映射到颜色梯度"""
        idx = min(len(HEATMAP_COLORS) - 1, int(value * len(HEATMAP_COLORS)))
        return HEATMAP_COLORS[idx]

    def _draw_heatmap(self, surface: pygame.Surface) -> None:
        """绘制压力/脚流量热力图叠加层"""
        pm = getattr(self, '_pressure_map', None)
        if pm is None:
            return
        for x in range(MAP_WIDTH):
            for y in range(MAP_HEIGHT):
                score = pm.get_score(x, y)
                color = self._get_heat_color(score)
                overlay = pygame.Surface((TILE_SIZE, TILE_SIZE))
                overlay.set_alpha(HEATMAP_ALPHA)
                overlay.fill(color)
                surface.blit(overlay, (x * TILE_SIZE, y * TILE_SIZE))

    def _draw_tile_grid(
        self,
        surface: pygame.Surface,
        game_map: object,
    ) -> None:
        """每个tile显示类型缩写"""
        for x in range(MAP_WIDTH):
            for y in range(MAP_HEIGHT):
                tile = game_map.get_tile(x, y)
                label = TILE_LABELS.get(tile, "?")
                text = self._font.render(label, True, (180, 180, 180))
                surface.blit(text, (x * TILE_SIZE + 2, y * TILE_SIZE + 2))

    def _draw_npc_stats(
        self,
        surface: pygame.Surface,
        npcs: list,
    ) -> None:
        """NPC头顶显示H/E数值"""
        for npc in npcs:
            cx = npc.x * TILE_SIZE + TILE_SIZE // 2
            cy = npc.y * TILE_SIZE + TILE_SIZE // 2
            text = self._font.render(
                f"H:{int(npc.hunger)} E:{int(npc.energy)}", True, COLOR_BLACK)
            tw, th = text.get_size()
            bx = cx - tw // 2 - 2
            by = cy - TILE_SIZE // 2 - th - 2
            pygame.draw.rect(surface, (255, 255, 255), (bx, by, tw + 4, th + 2))
            surface.blit(text, (cx - tw // 2, by + 1))

    def _draw_paths(
        self,
        surface: pygame.Surface,
        npcs: list,
    ) -> None:
        """A*路径线段 + 目标红点"""
        for npc in npcs:
            path = getattr(npc, '_path', [])
            if path:
                pts = [(npc.x, npc.y)] + path
                for i in range(len(pts) - 1):
                    x1 = pts[i][0] * TILE_SIZE + TILE_SIZE // 2
                    y1 = pts[i][1] * TILE_SIZE + TILE_SIZE // 2
                    x2 = pts[i + 1][0] * TILE_SIZE + TILE_SIZE // 2
                    y2 = pts[i + 1][1] * TILE_SIZE + TILE_SIZE // 2
                    pygame.draw.line(surface, (255, 100, 100),
                                     (x1, y1), (x2, y2), 2)
                tx = path[-1][0] * TILE_SIZE + TILE_SIZE // 2
                ty = path[-1][1] * TILE_SIZE + TILE_SIZE // 2
                pygame.draw.circle(surface, (255, 0, 0), (tx, ty), 5)
            elif (npc.target_x is not None and npc.target_y is not None):
                sx = npc.x * TILE_SIZE + TILE_SIZE // 2
                sy = npc.y * TILE_SIZE + TILE_SIZE // 2
                ex = npc.target_x * TILE_SIZE + TILE_SIZE // 2
                ey = npc.target_y * TILE_SIZE + TILE_SIZE // 2
                pygame.draw.line(surface, (255, 100, 100), (sx, sy), (ex, ey), 2)
                pygame.draw.circle(surface, (255, 0, 0), (ex, ey), 4)
