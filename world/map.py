"""
地图模块 — 孤岛tile地图生成与渲染

提供GameMap类，管理20x20网格地图、地形生成和tile渲染。
"""

import math
import pygame
from config import MAP_WIDTH, MAP_HEIGHT, TILE_SIZE, TileType, TILE_COLORS, TILE_PROPERTIES


class GameMap:
    """孤岛tile地图"""

    def __init__(self) -> None:
        """初始化20x20地图，生成孤岛地形"""
        self._grid: list[list[TileType]] = [
            [TileType.WATER for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)
        ]
        self._generate_terrain()
        self._place_structures()

    def _generate_terrain(self) -> None:
        """生成孤岛地形：中心陆地、沙滩边缘、外围海水"""
        cx, cy = MAP_WIDTH // 2, MAP_HEIGHT // 2
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                dx, dy = x - cx, y - cy
                dist = math.sqrt(dx * dx + dy * dy)

                if dist <= 7.5:
                    # 内圈：草地、森林、岩石
                    if (x * 7 + y * 3) % 11 == 0:
                        self._grid[y][x] = TileType.FOREST
                    elif (x, y) in [(14, 7), (6, 14)]:
                        self._grid[y][x] = TileType.ROCK
                    else:
                        self._grid[y][x] = TileType.GRASS
                elif dist <= 8.5:
                    # 沙滩过渡带
                    self._grid[y][x] = TileType.SAND
                # else: 保持WATER

    def _place_structures(self) -> None:
        """放置建筑物：5个房屋和1个篝火在村落中心"""
        # 5个房屋（对应5个NPC）
        house_positions = [(8, 8), (12, 8), (8, 12), (12, 12), (10, 6)]
        for x, y in house_positions:
            self._grid[y][x] = TileType.HOUSE
        # 村落中心的篝火
        self._grid[10][10] = TileType.CAMPFIRE

    def get_tile(self, x: int, y: int) -> TileType | None:
        """获取指定坐标的tile类型"""
        if not (0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT):
            return None
        return self._grid[y][x]

    def is_walkable(self, x: int, y: int) -> bool:
        """判断指定坐标是否可行走（由TILE_PROPERTIES驱动）"""
        tile = self.get_tile(x, y)
        if tile is None:
            return False
        props = TILE_PROPERTIES.get(tile, {})
        return bool(props.get("walkable", False))

    def draw(self, surface: pygame.Surface) -> None:
        """将地图渲染到pygame surface"""
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                tile = self._grid[y][x]
                color = TILE_COLORS[tile]
                rect = pygame.Rect(
                    x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE
                )
                pygame.draw.rect(surface, color, rect)

    def get_houses(self) -> list[tuple[int, int]]:
        """返回所有房屋的坐标列表"""
        houses: list[tuple[int, int]] = []
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                if self._grid[y][x] == TileType.HOUSE:
                    houses.append((x, y))
        return houses
