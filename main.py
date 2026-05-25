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
    MAP_HEIGHT,
    MAP_WIDTH,
    NPC_INITIAL_DATA,
    NPC_NAME_PINYIN,
    OVERLAY_NONE,
    OVERLAY_TILE,
    OVERLAY_STATS,
    OVERLAY_PATH,
    SIDEBAR_WIDTH,
    STATE_COLORS,
    TILE_LABELS,
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


def draw_npcs(surface: pygame.Surface, npcs: list[NPC],
              font_tiny: pygame.font.Font) -> None:
    """在map上绘制NPC彩色圆形 + 头顶状态标签"""
    for i, npc in enumerate(npcs):
        cx = npc.x * TILE_SIZE + TILE_SIZE // 2
        cy = npc.y * TILE_SIZE + TILE_SIZE // 2
        radius = TILE_SIZE // 2 - 3

        # 按状态选颜色
        state = npc.get_state()
        color = STATE_COLORS.get(state, COLOR_WHITE)
        pygame.draw.circle(surface, color, (cx, cy), radius)
        pygame.draw.circle(surface, COLOR_BLACK, (cx, cy), radius, 2)

        # ── 头顶标签：名字（拼音）+ 状态 ──
        pinyin = NPC_NAME_PINYIN.get(npc.name, npc.name)
        name_surf = font_tiny.render(pinyin, True, COLOR_BLACK)
        state_surf = font_tiny.render(state, True, COLOR_BLACK)

        nw = name_surf.get_width()
        sw = state_surf.get_width()
        label_w = max(nw, sw) + 4
        label_h = font_tiny.get_height() * 2 + 4

        # 标签Y位置在圆上方
        lx = cx - label_w // 2
        ly = cy - radius - label_h

        pygame.draw.rect(surface, (255, 255, 255), (lx, ly, label_w, label_h))
        pygame.draw.rect(surface, COLOR_BLACK, (lx, ly, label_w, label_h), 1)
        surface.blit(name_surf, (cx - nw // 2, ly + 2))
        surface.blit(state_surf, (cx - sw // 2, ly + 2 + font_tiny.get_height()))


def draw_debug_overlay(surface: pygame.Surface, npcs: list[NPC],
                       game_map: GameMap, overlay_mode: int,
                       font_small: pygame.font.Font) -> None:
    """F1-Tile网格, F2-Hunger/Energy数值, F3-目标路径"""
    if overlay_mode == OVERLAY_TILE:
        for x in range(MAP_WIDTH):
            for y in range(MAP_HEIGHT):
                label = TILE_LABELS.get(game_map.get_tile(x, y), "?")
                text = font_small.render(label, True, (180, 180, 180))
                surface.blit(text, (x * TILE_SIZE + 2, y * TILE_SIZE + 2))

    elif overlay_mode == OVERLAY_STATS:
        for npc in npcs:
            cx = npc.x * TILE_SIZE + TILE_SIZE // 2
            cy = npc.y * TILE_SIZE + TILE_SIZE // 2
            text = font_small.render(
                f"H:{int(npc.hunger)} E:{int(npc.energy)}", True, COLOR_BLACK)
            tw, th = text.get_size()
            bx = cx - tw // 2 - 2
            by = cy - TILE_SIZE // 2 - th - 2
            pygame.draw.rect(surface, (255, 255, 255), (bx, by, tw + 4, th + 2))
            surface.blit(text, (cx - tw // 2, by + 1))

    elif overlay_mode == OVERLAY_PATH:
        for npc in npcs:
            if npc.target_x is not None and npc.target_y is not None:
                start = (npc.x * TILE_SIZE + TILE_SIZE // 2,
                         npc.y * TILE_SIZE + TILE_SIZE // 2)
                end = (npc.target_x * TILE_SIZE + TILE_SIZE // 2,
                       npc.target_y * TILE_SIZE + TILE_SIZE // 2)
                pygame.draw.line(surface, (255, 100, 100), start, end, 2)
                pygame.draw.circle(surface, (255, 0, 0), end, 4)


def draw_sidebar(surface: pygame.Surface, npcs: list[NPC],
                 font: pygame.font.Font, font_small: pygame.font.Font,
                 time_str: str) -> None:
    """绘制右侧状态栏：时间 + 每个NPC的状态信息"""
    sidebar_x = MAP_WIDTH * TILE_SIZE
    pygame.draw.rect(surface, COLOR_SIDEBAR_BG,
                     (sidebar_x, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT))

    # 时间
    time_surf = font.render(time_str, True, COLOR_WHITE)
    surface.blit(time_surf, (sidebar_x + 8, 8))

    # NPC列表
    y = 36
    for i, npc in enumerate(npcs):
        info = npc.get_sidebar_info()
        # 颜色小圆点（用NPC个体色便于区分身份）
        pygame.draw.circle(surface, NPC_COLORS[i],
                           (sidebar_x + 12, y + 7), 5)
        # 名称（拼音） + 状态
        pinyin = NPC_NAME_PINYIN.get(info["name"], info["name"])
        line1 = font.render(
            f"{pinyin} [{info['state']}]", True, COLOR_WHITE)
        # 属性
        line2 = font_small.render(
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
    font_small = pygame.font.Font(None, 14)
    font_tiny = pygame.font.Font(None, 12)

    # --test 模式：运行3秒(180帧@60fps)后自动退出
    test_mode = "--test" in sys.argv
    test_counter = 180

    # Debug overlay模式（F1-F4切换）
    overlay_mode = OVERLAY_NONE

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
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F1:
                    overlay_mode = OVERLAY_TILE
                elif event.key == pygame.K_F2:
                    overlay_mode = OVERLAY_STATS
                elif event.key == pygame.K_F3:
                    overlay_mode = OVERLAY_PATH
                elif event.key == pygame.K_F4:
                    overlay_mode = OVERLAY_NONE

        # ── 逻辑更新 ──
        time_system.tick()
        for npc in npcs:
            npc.update()

        # ── 渲染 ──
        game_map.draw(screen)
        draw_npcs(screen, npcs, font_tiny)
        if overlay_mode != OVERLAY_NONE:
            draw_debug_overlay(screen, npcs, game_map, overlay_mode, font_small)
        draw_sidebar(screen, npcs, font, font_small, time_system.get_time_string())

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
