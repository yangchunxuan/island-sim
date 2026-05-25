"""
主游戏入口 — Island Sim v1

初始化pygame窗口、创建游戏对象、管理主循环（update + draw）。
支持 --test 参数（运行3秒后自动退出）。
"""

import sys

import pygame

from config import (
    COLOR_BLACK,
    COLOR_SIDEBAR_BG,
    COLOR_WHITE,
    FPS,
    MAP_WIDTH,
    NPC_INITIAL_DATA,
    SIDEBAR_WIDTH,
    TILE_SIZE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from npc.behavior import register_npc_states
from npc.memory import Memory
from npc.npc import NPC, NPC_COLORS
from npc.relationship import RelationshipSystem
from world.map import GameMap
from world.time_system import TimeSystem


def draw_npcs(surface: pygame.Surface, npcs: list[NPC]) -> None:
    """在map上绘制NPC彩色圆形"""
    for i, npc in enumerate(npcs):
        cx = npc.x * TILE_SIZE + TILE_SIZE // 2
        cy = npc.y * TILE_SIZE + TILE_SIZE // 2
        # 填充圆
        pygame.draw.circle(surface, NPC_COLORS[i], (cx, cy), TILE_SIZE // 2 - 3)
        # 黑色边框
        pygame.draw.circle(surface, COLOR_BLACK, (cx, cy), TILE_SIZE // 2 - 3, 2)


def draw_sidebar(surface: pygame.Surface, npcs: list[NPC],
                 font: pygame.font.Font, time_str: str) -> None:
    """绘制右侧状态栏：时间 + 每个NPC的状态信息"""
    sidebar_x = MAP_WIDTH * TILE_SIZE
    # 背景
    pygame.draw.rect(surface, COLOR_SIDEBAR_BG,
                     (sidebar_x, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT))

    # 时间
    time_surf = font.render(time_str, True, COLOR_WHITE)
    surface.blit(time_surf, (sidebar_x + 8, 8))

    # NPC列表
    y = 36
    for i, npc in enumerate(npcs):
        info = npc.get_sidebar_info()
        # 颜色小圆点
        pygame.draw.circle(surface, NPC_COLORS[i],
                           (sidebar_x + 12, y + 7), 5)
        # 名称 + 状态
        line1 = font.render(
            f"{info['name']} [{info['state']}]", True, COLOR_WHITE)
        # 属性
        line2 = font.render(
            f"H:{info['hunger']:3d} E:{info['energy']:3d} M:{info['mood']:3d}",
            True, COLOR_WHITE)
        surface.blit(line1, (sidebar_x + 24, y))
        surface.blit(line2, (sidebar_x + 24, y + 16))
        y += 40


def main() -> None:
    """游戏主函数"""
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("孤岛世界 v1")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 18)

    # --test 模式：运行3秒(180帧@60fps)后自动退出
    test_mode = "--test" in sys.argv
    test_counter = 180

    # 创建游戏对象
    game_map = GameMap()
    time_system = TimeSystem()

    npcs: list[NPC] = []
    for data in NPC_INITIAL_DATA:
        npc = NPC(data, time_system, game_map)
        register_npc_states(npc)
        npcs.append(npc)

    # 预留接口
    memories = [Memory() for _ in npcs]
    relationship = RelationshipSystem()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # ── 逻辑更新 ──
        time_system.tick()
        for npc in npcs:
            npc.update()

        # ── 渲染 ──
        game_map.draw(screen)
        draw_npcs(screen, npcs)
        draw_sidebar(screen, npcs, font, time_system.get_time_string())

        pygame.display.flip()
        clock.tick(FPS)

        # test模式倒计时
        if test_mode:
            test_counter -= 1
            if test_counter <= 0:
                running = False

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
