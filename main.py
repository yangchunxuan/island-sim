"""
主游戏入口 — Island Sim v1

初始化pygame窗口、创建游戏对象、管理主循环（update + draw）。
支持 --test 参数（运行3秒后自动退出）。
支持 --headless 参数（无渲染加速模拟）。
支持 --simulate-days N 参数（运行N天后自动停止输出统计）。
"""

import json
import os
import sys

import pygame

from config import (
    DAY_TICKS,
    FPS,
    HEADLESS_TICK_RATE,
    NPC_INITIAL_DATA,
    OVERLAY_HEATMAP,
    OVERLAY_NONE,
    OVERLAY_TILE,
    OVERLAY_STATS,
    OVERLAY_PATH,
)
from npc.behavior import register_npc_states
from npc.memory import Memory
from npc.npc import NPC
from npc.relationship import RelationshipSystem
from observer import WorldObserver
from render import Renderer
from world.map import GameMap
from world.regional_pressure import RegionPressureMap
from world.resources import ResourceManager
from world.time_system import TimeSystem


def _create_game_objects():
    """创建所有游戏对象（普通模式和headless模式共用）"""
    game_map = GameMap()
    time_system = TimeSystem()
    resource_mgr = ResourceManager(game_map._grid)
    pressure_map = RegionPressureMap(game_map._grid)
    resource_mgr.set_pressure_map(pressure_map)

    npcs: list[NPC] = []
    for data in NPC_INITIAL_DATA:
        npc = NPC(data, time_system, game_map, resource_mgr=resource_mgr)
        register_npc_states(npc)
        npcs.append(npc)

    observer = WorldObserver()
    observer.set_pressure_map(pressure_map)

    return game_map, time_system, resource_mgr, pressure_map, npcs, observer


def _save_headless_stats(observer: WorldObserver, time_system: TimeSystem,
                          resource_mgr: object, days: int) -> None:
    """保存headless模式统计到world_reports/statistics.json"""
    stats_dir = os.path.join(os.path.dirname(__file__), "world_reports")
    os.makedirs(stats_dir, exist_ok=True)
    report_dir = os.path.join(os.path.dirname(__file__), "world_reports")
    events = observer.event_logger.get_events_since(0)
    memory_summary = {}
    if hasattr(observer, '_memory') and observer._memory is not None:
        memory_summary = observer._memory.get_summary()

    stats = {
        "days_simulated": days,
        "total_ticks": time_system._tick_count,
        "total_events": len(events),
        "event_types": {},
        "resource": {
            "total_food": resource_mgr.total_food_remaining(),
            "depleted_forests": len(resource_mgr.depleted_forests),
        },
        "npc_final_state": {},
        "world_history": memory_summary,
    }
    for e in events:
        et = e["event_type"]
        stats["event_types"][et] = stats["event_types"].get(et, 0) + 1

    path = os.path.join(stats_dir, "statistics.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"[HEADLESS] Statistics saved to {path}")


def run_headless(days: int) -> None:
    """headless模式：无渲染高速运行N天"""
    _, time_system, resource_mgr, _, npcs, observer = _create_game_objects()
    target_ticks = days * DAY_TICKS

    print(f"[HEADLESS] Simulating {days} days ({target_ticks} ticks)...")
    tick = 0
    while tick < target_ticks:
        time_system.tick()
        for npc in npcs:
            npc.update()
        observer.update(time_system._tick_count, resource_mgr, npcs)
        tick = time_system._tick_count

        if tick % (DAY_TICKS * 10) == 0 and tick > 0:
            pct = tick * 100 // target_ticks
            day = tick // DAY_TICKS
            print(f"[HEADLESS] Day {day} ({pct}%) - "
                  f"hunger_avg={sum(n.hunger for n in npcs)/len(npcs):.0f}")

    _save_headless_stats(observer, time_system, resource_mgr, days)
    print(f"[HEADLESS] Done. {days} days simulated ({tick} ticks).")


def main() -> None:
    """游戏主函数"""
    # ── 参数解析 ──
    headless_mode = "--headless" in sys.argv
    simulate_days = 0
    for i, arg in enumerate(sys.argv):
        if arg == "--simulate-days" and i + 1 < len(sys.argv):
            try:
                simulate_days = int(sys.argv[i + 1])
            except ValueError:
                pass

    if headless_mode and simulate_days > 0:
        run_headless(simulate_days)
        sys.exit(0)

    # --test 模式：运行3秒(180帧@60fps)后自动退出
    test_mode = "--test" in sys.argv
    test_counter = 180

    pygame.init()
    clock = pygame.time.Clock()

    # Debug overlay模式（F1-F4切换）
    overlay_mode = OVERLAY_NONE

    # 创建游戏对象
    game_map, time_system, resource_mgr, pressure_map, npcs, observer = \
        _create_game_objects()

    # 预留接口
    memories = [Memory() for _ in npcs]
    relationship = RelationshipSystem()

    # 创建渲染器
    renderer = Renderer()
    renderer.set_game_objects(game_map, resource_mgr, time_system, npcs)
    renderer.set_pressure_map(pressure_map)

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
                elif event.key == pygame.K_F5:
                    overlay_mode = OVERLAY_HEATMAP

        # ── 逻辑更新 ──
        time_system.tick()
        for npc in npcs:
            npc.update()

        # ── 世界观察 ──
        observer.update(time_system._tick_count, resource_mgr, npcs)

        # ── 渲染（由Renderer统一处理）──
        renderer.draw(overlay_mode)

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


if __name__ == "__main__":
    main()
