"""
NPC行为状态模块 — Island Sim v1

定义IDLE/WALK/SEARCH_FOOD/EAT/SLEEP五个状态，实现完整行为循环：
IDLE → WALK → IDLE（自由漫游）
hunger>70 → SEARCH_FOOD → WALK(到森林) → EAT → IDLE
energy<20 / 夜晚 → SLEEP(到房屋) → 恢复能量 → IDLE

使用A*寻路替代随机漫步，目标驱动。
"""

import random
from typing import Optional

from config import STAT_MIN, STAT_MAX, TileType
from systems.pathfinding import astar
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
    """行走状态：沿A*路径一步步移动"""

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
            # 目标不可达，取消本次行走
            owner.target_x = None
            owner.target_y = None
            owner._path = []
            owner.fsm.set_state("IDLE", owner)
            return
        owner._path = path

    def update(self, owner: object) -> None:
        """每帧从路径中弹出一步（每5帧实际移动一次）"""
        if not owner._path:
            # 路径为空：到达目标或没有路径
            purpose = owner._walk_purpose
            owner._walk_purpose = "IDLE"
            owner.target_x = None
            owner.target_y = None
            if purpose == "EAT":
                owner.fsm.set_state("EAT", owner)
            elif purpose == "SLEEP":
                # 到达房屋，开始睡觉
                owner.fsm.set_state("SLEEP", owner)
            else:
                owner.fsm.set_state("IDLE", owner)
            return

        # 移动冷却
        owner._move_cooldown -= 1
        if owner._move_cooldown > 0:
            return
        owner._move_cooldown = 5

        # 路径由A*保证全是walkable
        next_x, next_y = owner._path.pop(0)
        owner.x, owner.y = next_x, next_y

        # 如果路径走到最后一步，下一帧会触发上面的空路径判断


class SearchFoodState(State):
    """觅食状态：找到最近的FOREST tile并用A*寻路过去"""

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
        """扫描全图，返回距离最近的FOREST tile"""
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
        # 已在房屋或找不到房屋：原地睡觉

    def update(self, owner: object) -> None:
        """每帧恢复能量0.5点"""
        owner.energy = min(STAT_MAX, owner.energy + 0.5)

    @staticmethod
    def _is_at_house(owner: object) -> bool:
        """检查NPC当前是否站在HOUSE tile上"""
        tile = owner._map.get_tile(owner.x, owner.y)
        return tile == TileType.HOUSE

    @staticmethod
    def _find_nearest_house(owner: object) -> Optional[tuple[int, int]]:
        """从地图上找到最近的HOUSE tile坐标"""
        game_map: GameMap = owner._map
        houses = game_map.get_houses()
        if not houses:
            return None
        return min(
            houses,
            key=lambda h: (h[0] - owner.x) ** 2 + (h[1] - owner.y) ** 2,
        )
