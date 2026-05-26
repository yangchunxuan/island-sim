"""
T-029 文字直播模式 — 无UI纯文字世界模拟

检测游戏状态变化（FSM切换、昼夜交替、资源变化、NPC相遇）
并输出中文事件文字。不和pygame交互。
"""

import contextlib
import os
import signal
import sys
import time
from typing import Any, Optional

from config import DAY_TICKS, NPC_INITIAL_DATA, TileType
from npc.ai_brain import AIBrain
from npc.behavior import register_npc_states
from npc.npc import NPC
from world.map import GameMap
from world.regional_pressure import RegionPressureMap
from world.resources import ResourceManager
from world.time_system import TimeSystem


def _region_name(x: int, y: int) -> str:
    """坐标到中文区域名（四象限）"""
    if x < 10 and y < 10:
        return "西北部"
    if x >= 10 and y < 10:
        return "东北部"
    if x < 10 and y >= 10:
        return "西南部"
    return "东南部"


def _tile_name(tile_type: TileType) -> str:
    """Tile类型转中文"""
    names = {
        TileType.WATER: "水边",
        TileType.SAND: "沙滩",
        TileType.GRASS: "草地",
        TileType.FOREST: "森林",
        TileType.ROCK: "岩石",
        TileType.HOUSE: "房屋",
        TileType.CAMPFIRE: "篝火旁",
    }
    return names.get(tile_type, "未知")


def _get_tile_at(npc: NPC) -> TileType:
    """获取NPC所在tile类型"""
    return npc._map.get_tile(npc.x, npc.y)


# FSM状态切换 → 中文描述
# (old_state, new_state) -> format_string
FSM_MESSAGES: dict[tuple[str, str], str] = {
    ("IDLE", "WALK"): "{name} 开始四处走动",
    ("IDLE", "SEARCH_FOOD"): "{name} 感到饥饿，前往寻找食物",
    ("IDLE", "SLEEP"): "{name} 准备休息",
    ("WALK", "IDLE"): "{name} 停了下来",
    ("WALK", "EAT"): "{name} 到达食物地点，开始进食",
    ("WALK", "SLEEP"): "{name} 到达住所，准备休息",
    ("SEARCH_FOOD", "WALK"): "{name} 发现食物，前往采集",
    ("SEARCH_FOOD", "IDLE"): "{name} 四处寻找但没有找到食物",
    ("EAT", "IDLE"): "{name} 吃饱了",
    ("SLEEP", "IDLE"): "{name} 醒来开始新的一天",
    ("SLEEP", "WALK"): "{name} 离开住所外出活动",
}

# 兜底描述（无精确匹配时用）
FSM_FALLBACK: dict[str, str] = {
    "IDLE": "{name} 开始发呆",
    "WALK": "{name} 开始移动",
    "SEARCH_FOOD": "{name} 开始寻找食物",
    "EAT": "{name} 开始吃东西",
    "SLEEP": "{name} 开始睡觉",
}

# Tile类型 → 相遇时的活动描述
ENCOUNTER_TILE_VERBS: dict[TileType, str] = {
    TileType.GRASS: "相遇",
    TileType.SAND: "相遇",
    TileType.FOREST: "在森林中相遇",
    TileType.CAMPFIRE: "在篝火旁相遇",
    TileType.HOUSE: "在房屋旁相遇",
    TileType.ROCK: "在岩石旁相遇",
    TileType.WATER: "在水边相遇",
}

FOOD_TYPE_NAMES = {
    "forest": "森林果实",
    "mushroom": "蘑菇",
    "fish": "鱼",
}


def _create_game_objects():
    """创建游戏对象（无pygame版本，不创建observer）"""
    game_map = GameMap()
    time_system = TimeSystem()
    resource_mgr = ResourceManager(game_map._grid)
    pressure_map = RegionPressureMap(game_map._grid)
    resource_mgr.set_pressure_map(pressure_map)
    resource_mgr.set_time_system(time_system)

    ai_brain = AIBrain()

    npcs: list[NPC] = []
    for data in NPC_INITIAL_DATA:
        npc = NPC(data, time_system, game_map, resource_mgr=resource_mgr, ai_brain=ai_brain)
        register_npc_states(npc)
        npcs.append(npc)

    NPC.set_all_npcs(npcs)
    return game_map, time_system, resource_mgr, pressure_map, npcs


class TextSimulation:
    """文字直播模式：无头运行游戏 + 检测变化 + 中文事件输出"""

    def __init__(self, speed: float = 5.0) -> None:
        """
        Args:
            speed: 每游戏天对应的现实秒数。0=尽可能快（无sleep）。
        """
        self.speed = max(0.0, speed)
        self._running = True

        # ── 游戏对象 ──
        self.game_map, self.time_system, self.resource_mgr, _, self.npcs = \
            _create_game_objects()

        # ── 状态快照（用于检测变化） ──
        self._prev_npc: dict[str, dict[str, Any]] = {}
        # npc_name -> {state, x, y, hunger, energy, weakened}
        self._prev_is_day: Optional[bool] = None
        self._prev_day_count: int = -1
        self._prev_season: str = ""
        self._prev_depleted: set[tuple[int, int]] = set()
        self._prev_nearby_pairs: set[tuple[str, str]] = set()
        self._prev_mushroom_count: int = 0
        self._prev_fish_count: int = 0
        self._last_summary_day: int = -1

        # ── 缓存（避免重复输出） ──
        self._last_encounter_message: str = ""
        self._init_snapshots()

        signal.signal(signal.SIGINT, self._handle_sigint)

    def _handle_sigint(self, sig, frame) -> None:
        """Ctrl+C 优雅退出"""
        self._running = False
        print()

    def _init_snapshots(self) -> None:
        """初始化所有NPC快照"""
        for npc in self.npcs:
            self._prev_npc[npc.name] = self._snapshot_npc(npc)
        self._prev_is_day = self.time_system.is_day()
        self._prev_day_count = self.time_system.get_day_count()
        self._prev_season = self.time_system.get_season()
        self._prev_depleted = set(self.resource_mgr.depleted_forests)
        self._prev_mushroom_count = len(self.resource_mgr.mushrooms)
        self._prev_fish_count = len(self.resource_mgr.fish)

    @staticmethod
    def _snapshot_npc(npc: NPC) -> dict[str, Any]:
        return {
            "state": npc.get_state(),
            "x": npc.x,
            "y": npc.y,
            "hunger": int(npc.hunger),
            "energy": int(npc.energy),
            "weakened": npc._weakened,
        }

    def _ts(self) -> str:
        """返回 [Day X, HH:MM] 格式时间戳"""
        hour = self.time_system.get_hour()
        hh = int(hour)
        mm = int((hour - hh) * 60)
        day = self.time_system.get_day_count()
        return f"[Day {day}, {hh:02d}:{mm:02d}]"

    # ══════════════════════════════════════════
    # 主循环
    # ══════════════════════════════════════════

    def run(self) -> None:
        """启动文字直播模式"""
        print()
        print("╔" + "═" * 58 + "╗")
        print(f"║  文字直播 — 世界模拟{' ' * 45}║")
        print("╚" + "═" * 58 + "╝")
        print()

        tick_delay = self.speed / DAY_TICKS  # 秒/每tick

        # 抑制底层模块的 [NPC]、[WORLD]、[ECO] 等调试打印
        devnull = open(os.devnull, 'w')

        while self._running:
            self.time_system.tick()
            with contextlib.redirect_stdout(devnull):
                for npc in self.npcs:
                    npc.update()
                self.resource_mgr.update()

            self._detect_all()

            if tick_delay > 0:
                time.sleep(tick_delay)

        total_days = self.time_system.get_day_count()
        devnull.close()
        print(f"[文字模式] 模拟结束 — 共 {total_days} 天")

    # ══════════════════════════════════════════
    # 事件检测
    # ══════════════════════════════════════════

    def _detect_all(self) -> None:
        """执行所有事件检测（每tick调用）"""
        self._detect_day_change()
        self._detect_dawn_dusk()
        self._detect_season_change()
        self._detect_npc_states()
        self._detect_encounters()
        self._detect_resource_events()
        self._detect_npc_weakened()

    def _detect_day_change(self) -> None:
        """检测天数变化 → 输出日间摘要"""
        day = self.time_system.get_day_count()
        if day != self._prev_day_count:
            self._prev_day_count = day
            ts = self._ts()
            total_food = self.resource_mgr.total_food_remaining()
            depleted = len(self.resource_mgr.depleted_forests)
            total_forest = self.resource_mgr.forest_count()
            print(f"{ts} ── 第 {day} 天 | 食物剩余 {total_food} | "
                  f"森林 {total_forest - depleted}/{total_forest} ──")

    def _detect_dawn_dusk(self) -> None:
        """检测日出/日落（NPC的SLEEP→IDLE由_detect_npc_states处理）"""
        current_is_day = self.time_system.is_day()
        if self._prev_is_day is not None and current_is_day != self._prev_is_day:
            ts = self._ts()
            if current_is_day:
                print(f"{ts} 🌅 天亮了")
            else:
                # 夜幕降临，统计还在外面的人
                outside = []
                for npc in self.npcs:
                    tile = _get_tile_at(npc)
                    if tile != TileType.HOUSE and npc.get_state() != "SLEEP":
                        outside.append(npc.name)
                if outside:
                    print(f"{ts} 🌙 夜幕降临，{'、'.join(outside)} 还在外面")
                else:
                    print(f"{ts} 🌙 夜幕降临")
        self._prev_is_day = current_is_day

    def _detect_season_change(self) -> None:
        """检测季节变化"""
        current_season = self.time_system.get_season()
        if current_season != self._prev_season:
            ts = self._ts()
            season_names = {"spring": "春天", "summer": "夏天",
                            "autumn": "秋天", "winter": "冬天"}
            name = season_names.get(current_season, current_season)
            print(f"{ts} 🍂 {name}来了")
        self._prev_season = current_season

    def _detect_npc_states(self) -> None:
        """检测NPC的FSM状态切换"""
        ts = self._ts()
        for npc in self.npcs:
            prev = self._prev_npc[npc.name]
            state = npc.get_state()

            if state != prev["state"]:
                msg = self._format_state(npc.name, prev["state"], state, npc)
                if msg:
                    print(f"{ts} {msg}")

            # 更新快照
            self._prev_npc[npc.name] = self._snapshot_npc(npc)

    def _format_state(self, name: str, old: str, new: str, npc: NPC) -> str:
        """格式化状态切换消息"""
        key = (old, new)

        # 精确匹配
        if key in FSM_MESSAGES:
            msg = FSM_MESSAGES[key].format(name=name)
        else:
            # 兜底：新状态描述
            pattern = FSM_FALLBACK.get(new, "{name} 状态变化: {old}→{new}")
            msg = pattern.format(name=name, old=old, new=new)

        # 补充位置信息（针对觅食和睡眠）
        if new == "SEARCH_FOOD":
            nearest = self.resource_mgr.find_nearest_food(npc.x, npc.y)
            if nearest:
                fx, fy, ftype = nearest
                fname = FOOD_TYPE_NAMES.get(ftype, ftype)
                region = _region_name(fx, fy)
                msg += f"（{region}有{fname}）"
        elif new == "SLEEP":
            tile = _get_tile_at(npc)
            if tile == TileType.HOUSE:
                msg += "（在房屋中）"

        return msg

    def _detect_npc_weakened(self) -> None:
        """检测NPC虚弱/恢复"""
        ts = self._ts()
        for npc in self.npcs:
            prev = self._prev_npc[npc.name]
            if npc._weakened and not prev["weakened"]:
                print(f"{ts} {npc.name} 因长时间饥饿变得虚弱")
            elif not npc._weakened and prev["weakened"]:
                print(f"{ts} {npc.name} 进食后恢复了体力")

    def _detect_encounters(self) -> None:
        """检测NPC相遇/分开"""
        # 计算当前相邻对
        current_pairs: set[tuple[str, str]] = set()
        pair_tiles: dict[tuple[str, str], TileType] = {}
        for i in range(len(self.npcs)):
            for j in range(i + 1, len(self.npcs)):
                a, b = self.npcs[i], self.npcs[j]
                dist = abs(a.x - b.x) + abs(a.y - b.y)
                if dist <= 2:
                    pair = (a.name, b.name)
                    current_pairs.add(pair)
                    # 取两人所在tile中"更有趣"的那个
                    tile = _get_tile_at(a)
                    if tile == TileType.CAMPFIRE:
                        pair_tiles[pair] = tile
                    else:
                        pair_tiles[pair] = _get_tile_at(b)

        ts = self._ts()

        # 新相遇
        new_pairs = current_pairs - self._prev_nearby_pairs
        for pair in new_pairs:
            tile = pair_tiles.get(pair, TileType.GRASS)
            verb = ENCOUNTER_TILE_VERBS.get(tile, "相遇")
            msg = f"{ts} {pair[0]} 和 {pair[1]} {verb}"
            if msg != self._last_encounter_message:
                print(f"{ts} {pair[0]} 和 {pair[1]} {verb}")
                self._last_encounter_message = msg

        # 分开（可选：安静地分开，不每对都输出）
        # parted = self._prev_nearby_pairs - current_pairs
        # for pair in parted:
        #     print(f"{ts} {pair[0]} 和 {pair[1]} 分开了")

        self._prev_nearby_pairs = current_pairs

    def _detect_resource_events(self) -> None:
        """检测资源变化：森林耗尽/恢复、食物总量变化等"""
        ts = self._ts()

        # 森林耗尽
        current_depleted = set(self.resource_mgr.depleted_forests)
        new_depleted = current_depleted - self._prev_depleted
        for pos in new_depleted:
            region = _region_name(pos[0], pos[1])
            print(f"{ts} {region}的森林食物已经耗尽")

        # 森林恢复
        recovered = self._prev_depleted - current_depleted
        for pos in recovered:
            region = _region_name(pos[0], pos[1])
            print(f"{ts} {region}的森林重新焕发生机，食物重新生长出来")

        self._prev_depleted = current_depleted

        # 食物总量变化（每隔几天输出概要）
        day = self.time_system.get_day_count()
        if day % 5 == 0 and day != self._last_summary_day and day > 0:
            self._last_summary_day = day
            total_food = self.resource_mgr.total_food_remaining()
            mush_count = len(self.resource_mgr.available_mushrooms())
            fish_count = len(self.resource_mgr.available_fish())
            parts = []
            if total_food >= 0:
                parts.append(f"剩余食物 {total_food}")
            if mush_count > 0:
                parts.append(f"蘑菇 {mush_count}")
            if fish_count > 0:
                parts.append(f"鱼 {fish_count}")
            if parts:
                print(f"{ts} 📊 资源概况 | {'、'.join(parts)}")
