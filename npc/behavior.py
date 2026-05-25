"""
NPC行为状态模块 — Island Sim v1

定义IDLE/WALK/SEARCH_FOOD/EAT/SLEEP五个状态，实现完整行为循环：
IDLE → WALK → IDLE（自由漫游）
hunger>70 → SEARCH_FOOD → WALK(到森林) → EAT → IDLE
energy<20 / 夜晚 → SLEEP
"""

import random
from typing import Optional

from config import STAT_MIN, STAT_MAX, TileType
from systems.state_machine import State
from world.map import GameMap


def register_npc_states(npc: object) -> None:
    """为NPC注册所有行为状态到FSM"""
    npc.fsm.add_state("IDLE", IdleState())
    npc.fsm.add_state("WALK", WalkState())
    npc.fsm.add_state("SEARCH_FOOD", SearchFoodState())
    npc.fsm.add_state("EAT", EatState())
    npc.fsm.add_state("SLEEP", SleepState())


class IdleState(State):
    """空闲状态：随机等待1-3秒后走向附近随机位置"""

    def enter(self, owner: object) -> None:
        """进入空闲，设置随机等待帧数（60-180帧）"""
        owner._idle_timer = random.randint(60, 180)

    def update(self, owner: object) -> None:
        """计时结束后切换为WALK"""
        owner._idle_timer -= 1
        if owner._idle_timer <= 0:
            target = self._pick_walk_target(owner)
            if target:
                owner.target_x, owner.target_y = target
                owner._walk_purpose = "IDLE"
                owner._move_cooldown = 0
                owner.fsm.set_state("WALK", owner)

    @staticmethod
    def _pick_walk_target(owner: object) -> Optional[tuple[int, int]]:
        """在当前位置附近随机选一个可行走tile"""
        game_map: GameMap = owner._map
        for _ in range(20):
            dx = random.randint(-3, 3)
            dy = random.randint(-3, 3)
            tx = max(0, min(19, owner.x + dx))
            ty = max(0, min(19, owner.y + dy))
            if game_map.is_walkable(tx, ty) and (tx, ty) != (owner.x, owner.y):
                return tx, ty
        return None


class WalkState(State):
    """行走状态：向目标tile一步步移动"""

    def update(self, owner: object) -> None:
        """每帧向目标方向移动一格（每5帧实际移动一次）"""
        if owner.target_x is None or owner.target_y is None:
            owner.fsm.set_state("IDLE", owner)
            return

        # 移动冷却
        owner._move_cooldown -= 1
        if owner._move_cooldown > 0:
            return
        owner._move_cooldown = 5

        game_map: GameMap = owner._map

        # 计算下一步坐标（优先水平方向）
        dx = owner.target_x - owner.x
        dy = owner.target_y - owner.y
        if abs(dx) >= abs(dy):
            nx = owner.x + (1 if dx > 0 else -1 if dx < 0 else 0)
            ny = owner.y
        else:
            nx = owner.x
            ny = owner.y + (1 if dy > 0 else -1 if dy < 0 else 0)

        # 检查是否到达目标
        if owner.x == owner.target_x and owner.y == owner.target_y:
            purpose = owner._walk_purpose
            owner._walk_purpose = "IDLE"
            if purpose == "EAT":
                owner.fsm.set_state("EAT", owner)
            else:
                owner.fsm.set_state("IDLE", owner)
            return

        # 移动（遇到障碍则放弃本次行走）
        if game_map.is_walkable(nx, ny):
            owner.x, owner.y = nx, ny
        else:
            owner.fsm.set_state("IDLE", owner)


class SearchFoodState(State):
    """觅食状态：找到最近的FOREST tile并走向它"""

    def enter(self, owner: object) -> None:
        """进入觅食，立即查找最近森林并切换为WALK"""
        target = self._find_nearest_forest(owner)
        if target:
            owner._walk_purpose = "EAT"
            owner.target_x, owner.target_y = target
            owner.fsm.set_state("WALK", owner)
        else:
            # 找不到森林（理论上不会发生），退回空闲
            owner.fsm.set_state("IDLE", owner)

    def update(self, owner: object) -> None:
        """不会被执行（enter已切换状态），保留以防万一"""
        pass

    @staticmethod
    def _find_nearest_forest(owner: object) -> Optional[tuple[int, int]]:
        """扫描全图，返回距离最近的可通行FOREST tile"""
        game_map: GameMap = owner._map
        best: Optional[tuple[int, int]] = None
        best_dist: float = float("inf")
        for y in range(20):
            for x in range(20):
                if game_map.get_tile(x, y) == TileType.FOREST:
                    dist = (x - owner.x) ** 2 + (y - owner.y) ** 2
                    if dist < best_dist:
                        best_dist = dist
                        best = (x, y)
        return best


class EatState(State):
    """进食状态：减少饥饿值（瞬时操作）"""

    def enter(self, owner: object) -> None:
        """进入进食，立即降低饥饿值30点"""
        owner.hunger = max(STAT_MIN, owner.hunger - 30)

    def update(self, owner: object) -> None:
        """进食完成，回到空闲"""
        owner.fsm.set_state("IDLE", owner)


class SleepState(State):
    """睡眠状态：每帧恢复能量"""

    def update(self, owner: object) -> None:
        """每帧恢复能量0.5点"""
        owner.energy = min(STAT_MAX, owner.energy + 0.5)
