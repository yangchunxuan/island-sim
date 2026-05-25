"""
NPC行为状态模块 — Island Sim v1 (生态升级)

T-017: SEARCH_FOOD/EAT 支持蘑菇/鱼，所有状态推动生态帧，行走记录人流量。
"""

import random
from typing import Optional

from config import (
    STAT_MIN,
    STAT_MAX,
    TileType,
    WEAKENED_MOVE_COOLDOWN,
    WEAKENED_IDLE_MULTIPLIER,
)
from systems.pathfinding import astar
from systems.state_machine import State
from world.map import GameMap


def _tick_eco(owner: object) -> None:
    """推进生态帧（从每个state的update调用，去重由ResourceManager处理）"""
    rm = getattr(owner, '_resource_mgr', None)
    if rm is not None:
        rm.update()


def register_npc_states(npc: object) -> None:
    """为NPC注册所有行为状态到FSM"""
    npc.fsm.add_state("IDLE", IdleState())
    npc.fsm.add_state("WALK", WalkState())
    npc.fsm.add_state("SEARCH_FOOD", SearchFoodState())
    npc.fsm.add_state("EAT", EatState())
    npc.fsm.add_state("SLEEP", SleepState())


def _is_weakened(owner: object) -> bool:
    """安全检查NPC是否处于weakened状态"""
    return bool(getattr(owner, '_weakened', False))


class IdleState(State):
    """空闲状态：weakened时空闲时间加倍"""

    def enter(self, owner: object) -> None:
        """进入空闲，设置随机等待帧数"""
        base = random.randint(60, 180)
        if _is_weakened(owner):
            base = int(base * WEAKENED_IDLE_MULTIPLIER)
        owner._idle_timer = base

    def update(self, owner: object) -> None:
        """计时结束后切换为WALK"""
        _tick_eco(owner)
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
    """行走状态：沿A*路径一步步移动，weakened时速度减半"""

    def enter(self, owner: object) -> None:
        """进入行走，用A*计算从当前位置到目标的路径"""
        if owner.target_x is None or owner.target_y is None:
            owner._path = []
            return

        path = astar(
            owner._map,
            (owner.x, owner.y),
            (owner.target_x, owner.target_y),
        )
        if path is None:
            owner.target_x = None
            owner.target_y = None
            owner._path = []
            owner.fsm.set_state("IDLE", owner)
            return
        owner._path = path

    def update(self, owner: object) -> None:
        """每帧从路径中弹出一步，记录人流量"""
        _tick_eco(owner)
        if not owner._path:
            purpose = owner._walk_purpose
            owner._walk_purpose = "IDLE"
            owner.target_x = None
            owner.target_y = None
            if purpose == "EAT":
                owner.fsm.set_state("EAT", owner)
            elif purpose == "SLEEP":
                owner.fsm.set_state("SLEEP", owner)
            else:
                owner.fsm.set_state("IDLE", owner)
            return

        owner._move_cooldown -= 1
        if owner._move_cooldown > 0:
            return
        owner._move_cooldown = WEAKENED_MOVE_COOLDOWN if _is_weakened(owner) else 5

        next_x, next_y = owner._path.pop(0)
        owner.x, owner.y = next_x, next_y

        # 记录人流量
        rm = getattr(owner, '_resource_mgr', None)
        if rm is not None:
            rm.record_traffic(next_x, next_y)


class SearchFoodState(State):
    """觅食状态：查找最近可用食物源（森林/蘑菇/鱼）并用A*走过去"""

    def enter(self, owner: object) -> None:
        """进入觅食，查找最近未耗尽的食物"""
        rm = getattr(owner, '_resource_mgr', None)
        if rm is not None:
            target = rm.find_nearest_food(owner.x, owner.y)
            if target:
                fx, fy, ftype = target
                owner._walk_purpose = "EAT"
                owner._walk_food_type = ftype  # 记录食物类型供EAT使用
                owner.target_x, owner.target_y = fx, fy
                owner.fsm.set_state("WALK", owner)
                return

        # 无可用食物，退回空闲
        owner.fsm.set_state("IDLE", owner)

    def update(self, owner: object) -> None:
        """不会被执行（enter已切换状态）"""
        pass


class EatState(State):
    """进食状态：消耗当前位置的食物（森林/蘑菇/鱼）"""

    def enter(self, owner: object) -> None:
        """消耗当前位置的食物降低饥饿值"""
        food_type = getattr(owner, '_walk_food_type', "forest")
        rm = getattr(owner, '_resource_mgr', None)
        nutrition = 0

        if rm is not None:
            if food_type == "forest":
                # 在当前tile及相邻tile寻找森林食物
                for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
                    if rm.collect(owner.x + dx, owner.y + dy) > 0:
                        nutrition = 30
                        break
                if nutrition == 0:
                    nutrition = 5  # 微量缓解
            else:
                nutrition = rm.collect_food_at(owner.x, owner.y, food_type)

        owner.hunger = max(STAT_MIN, owner.hunger - nutrition)
        owner._walk_food_type = "forest"  # 重置

    def update(self, owner: object) -> None:
        """进食完成，回到空闲"""
        _tick_eco(owner)
        owner.fsm.set_state("IDLE", owner)


class SleepState(State):
    """睡眠状态：先找最近房屋走过去，到达后每帧恢复能量"""

    def enter(self, owner: object) -> None:
        """进入睡眠时，如果不在房屋上则先导航过去"""
        if not self._is_at_house(owner):
            target = self._find_nearest_house(owner)
            if target:
                owner._walk_purpose = "SLEEP"
                owner.target_x, owner.target_y = target
                owner._move_cooldown = 0
                owner.fsm.set_state("WALK", owner)
                return

    def update(self, owner: object) -> None:
        """每帧恢复能量0.5点"""
        _tick_eco(owner)
        owner.energy = min(STAT_MAX, owner.energy + 0.5)

    @staticmethod
    def _is_at_house(owner: object) -> bool:
        tile = owner._map.get_tile(owner.x, owner.y)
        return tile == TileType.HOUSE

    @staticmethod
    def _find_nearest_house(owner: object) -> Optional[tuple[int, int]]:
        game_map: GameMap = owner._map
        houses = game_map.get_houses()
        if not houses:
            return None
        return min(
            houses,
            key=lambda h: (h[0] - owner.x) ** 2 + (h[1] - owner.y) ** 2,
        )
