"""
主游戏入口 — Island Sim v1

初始化pygame窗口、创建游戏对象、管理主循环（update + draw）。
支持 --test 参数（运行3秒后自动退出）。
"""

import sys

import pygame

from config import (
    COLOR_BLACK,
    COLOR_DEPLETED_FOREST,
    COLOR_SIDEBAR_BG,
    COLOR_WEAKENED_RING,
    COLOR_WHITE,
    FPS,
    HUD_DEPLETED_COLOR,
    HUD_FOOD_COLOR,
    HUD_MOOD_COLOR,
    HUD_WEAKENED_COLOR,
    MAP_HEIGHT,
    MAP_WIDTH,
    NIGHT_OVERLAY_ALPHA,
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
from world.resources import ResourceManager
from world.time_system import TimeSystem


def draw_npcs(surface: pygame.Surface, npcs: list[NPC],
              font_tiny: pygame.font.Font) -> None:
    """在map上绘制NPC彩色圆形 + 头顶状态标签 + weakened指示"""
    for i, npc in enumerate(npcs):
        cx = npc.x * TILE_SIZE + TILE_SIZE // 2
        cy = npc.y * TILE_SIZE + TILE_SIZE // 2
        radius = TILE_SIZE // 2 - 3

        # weakened NPC显示灰色外环
        weakened = getattr(npc, '_weakened', False)

        # 按状态选颜色
        state = npc.get_state()
        color = STATE_COLORS.get(state, COLOR_WHITE)

        if weakened:
            pygame.draw.circle(surface, COLOR_WEAKENED_RING, (cx, cy), radius + 3, 3)

        pygame.draw.circle(surface, color, (cx, cy), radius)
        pygame.draw.circle(surface, COLOR_BLACK, (cx, cy), radius, 2)

        # ── 头顶标签：名字（拼音）+ 状态 ──
        pinyin = NPC_NAME_PINYIN.get(npc.name, npc.name)
        label_state = state
        if weakened:
            label_state += " WEAK"
        name_surf = font_tiny.render(pinyin, True, COLOR_BLACK)
        state_surf = font_tiny.render(label_state, True, COLOR_BLACK)

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


def draw_depleted_forests(surface: pygame.Surface,
                          resource_mgr: ResourceManager | None) -> None:
    """在depleted森林上绘制灰绿色方块标记"""
    if resource_mgr is None:
        return
    for (fx, fy) in getattr(resource_mgr, '_depleted', set()):
        rect = pygame.Rect(fx * TILE_SIZE, fy * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        s = pygame.Surface((TILE_SIZE, TILE_SIZE))
        s.set_alpha(180)
        s.fill(COLOR_DEPLETED_FOREST)
        surface.blit(s, (fx * TILE_SIZE, fy * TILE_SIZE))
        # 画一个"X"标记
        cx = fx * TILE_SIZE + TILE_SIZE // 2
        cy = fy * TILE_SIZE + TILE_SIZE // 2
        pygame.draw.line(surface, (60, 60, 40), (cx - 6, cy - 6), (cx + 6, cy + 6), 2)
        pygame.draw.line(surface, (60, 60, 40), (cx + 6, cy - 6), (cx - 6, cy + 6), 2)


def draw_night_overlay(surface: pygame.Surface,
                       time_system: TimeSystem) -> None:
    """夜晚时在地图区域覆盖半透明黑色遮罩"""
    if time_system.is_night():
        overlay = pygame.Surface((MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE))
        overlay.set_alpha(NIGHT_OVERLAY_ALPHA)
        overlay.fill(COLOR_BLACK)
        surface.blit(overlay, (0, 0))


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
            path = getattr(npc, '_path', [])
            if path:
                # 绘制完整路径线段
                pts = [(npc.x, npc.y)] + path
                for i in range(len(pts) - 1):
                    x1 = pts[i][0] * TILE_SIZE + TILE_SIZE // 2
                    y1 = pts[i][1] * TILE_SIZE + TILE_SIZE // 2
                    x2 = pts[i + 1][0] * TILE_SIZE + TILE_SIZE // 2
                    y2 = pts[i + 1][1] * TILE_SIZE + TILE_SIZE // 2
                    pygame.draw.line(surface, (255, 100, 100), (x1, y1), (x2, y2), 2)
                # 目标点标记
                tx = path[-1][0] * TILE_SIZE + TILE_SIZE // 2
                ty = path[-1][1] * TILE_SIZE + TILE_SIZE // 2
                pygame.draw.circle(surface, (255, 0, 0), (tx, ty), 5)
            elif npc.target_x is not None and npc.target_y is not None:
                start = (npc.x * TILE_SIZE + TILE_SIZE // 2,
                         npc.y * TILE_SIZE + TILE_SIZE // 2)
                end = (npc.target_x * TILE_SIZE + TILE_SIZE // 2,
                       npc.target_y * TILE_SIZE + TILE_SIZE // 2)
                pygame.draw.line(surface, (255, 100, 100), start, end, 2)
                pygame.draw.circle(surface, (255, 0, 0), end, 4)


def draw_sidebar(surface: pygame.Surface, npcs: list[NPC],
                 font: pygame.font.Font, font_small: pygame.font.Font,
                 time_str: str,
                 resource_mgr: ResourceManager | None = None) -> None:
    """绘制右侧状态栏：时间 + NPC状态 + 世界HUD"""
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
        line1 = font.render(
            f"{pinyin} [{state_tag}]", True, COLOR_WHITE)
        # 属性
        line2 = font_small.render(
            f"H:{info['hunger']:3d} E:{info['energy']:3d} M:{info['mood']:3d}",
            True, COLOR_WHITE)
        surface.blit(line1, (sidebar_x + 24, y))
        surface.blit(line2, (sidebar_x + 24, y + 16))
        y += 40

    # ── 世界HUD（底部面板） ──
    if resource_mgr is not None:
        hud_y = WINDOW_HEIGHT - 100
        pygame.draw.line(surface, (80, 80, 80),
                         (sidebar_x + 4, hud_y - 4),
                         (sidebar_x + SIDEBAR_WIDTH - 4, hud_y - 4))
        hud_title = font.render("World", True, (200, 200, 200))
        surface.blit(hud_title, (sidebar_x + 8, hud_y))
        hud_y += 20

        total_food = resource_mgr.total_food_remaining()
        depleted_count = len(getattr(resource_mgr, '_depleted', set()))
        weakened_count = sum(1 for n in npcs if getattr(n, '_weakened', False))
        avg_mood = sum(n.mood for n in npcs) / len(npcs) if npcs else 0

        hud_lines = [
            (f"Food:{total_food:3d}", HUD_FOOD_COLOR),
            (f"Depleted:{depleted_count:2d}", HUD_DEPLETED_COLOR),
            (f"Weakened:{weakened_count:2d}", HUD_WEAKENED_COLOR),
            (f"Avg Mood:{avg_mood:3.0f}", HUD_MOOD_COLOR),
        ]
        for text, clr in hud_lines:
            line = font_small.render(text, True, clr)
            surface.blit(line, (sidebar_x + 12, hud_y))
            hud_y += 16


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
    resource_mgr = ResourceManager(game_map._grid)

    npcs: list[NPC] = []
    for data in NPC_INITIAL_DATA:
        npc = NPC(data, time_system, game_map, resource_mgr=resource_mgr)
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
        draw_depleted_forests(screen, resource_mgr)
        draw_npcs(screen, npcs, font_tiny)
        if overlay_mode != OVERLAY_NONE:
            draw_debug_overlay(screen, npcs, game_map, overlay_mode, font_small)
        draw_night_overlay(screen, time_system)
        draw_sidebar(screen, npcs, font, font_small,
                     time_system.get_time_string(), resource_mgr)

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
