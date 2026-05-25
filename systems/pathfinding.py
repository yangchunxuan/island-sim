"""
A*寻路模块 — Island Sim v1

在20x20 grid上使用A*算法寻路，避开不可walkable的tile。
四方向移动（上/下/左/右），曼哈顿距离启发函数。
"""

import heapq
from typing import Optional

from config import MAP_WIDTH, MAP_HEIGHT


def astar(
    game_map: "GameMap",
    start: tuple[int, int],
    goal: tuple[int, int],
) -> Optional[list[tuple[int, int]]]:
    """A*寻路，返回从start到goal的最短路径（不含起点，含终点）。

    参数：
        game_map — GameMap实例，用于is_walkable()检查
        start — 起点坐标 (x, y)
        goal — 终点坐标 (x, y)

    返回：
        路径坐标列表（从起点旁的第一步开始到goal），
        空列表表示已在目标点，
        None表示目标不可达或不可行走。
    """
    sx, sy = start
    gx, gy = goal

    # 边界检查
    if not (0 <= sx < MAP_WIDTH and 0 <= sy < MAP_HEIGHT):
        return None
    if not (0 <= gx < MAP_WIDTH and 0 <= gy < MAP_HEIGHT):
        return None

    # 目标不可步行
    if start != goal and not game_map.is_walkable(gx, gy):
        return None

    # 已在目标
    if start == goal:
        return []

    # A*主循环
    open_heap = [(0, start)]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0}
    f_score: dict[tuple[int, int], float] = {start: _heuristic(start, goal)}
    closed_set: set[tuple[int, int]] = set()

    while open_heap:
        _, current = heapq.heappop(open_heap)

        if current in closed_set:
            continue
        if current == goal:
            return _reconstruct_path(came_from, current)

        closed_set.add(current)

        for neighbor in _neighbors(current):
            nx, ny = neighbor

            # 边界检查
            if not (0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT):
                continue
            # 障碍检查
            if neighbor != goal and not game_map.is_walkable(nx, ny):
                continue
            if neighbor in closed_set:
                continue

            tentative_g = g_score[current] + 1
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + _heuristic(neighbor, goal)
                f_score[neighbor] = f
                heapq.heappush(open_heap, (f, neighbor))

    return None


def _heuristic(a: tuple[int, int], b: tuple[int, int]) -> int:
    """曼哈顿距离"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _neighbors(pos: tuple[int, int]) -> list[tuple[int, int]]:
    """四方向邻居"""
    x, y = pos
    return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]


def _reconstruct_path(
    came_from: dict[tuple[int, int], tuple[int, int]],
    current: tuple[int, int],
) -> list[tuple[int, int]]:
    """从came_from表重建路径（从起点到终点的顺序）"""
    path = []
    while current in came_from:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path
