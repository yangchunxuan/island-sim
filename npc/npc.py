"""
NPC角色模块 — Island Sim v1

定义NPC类，管理属性、状态机和每帧更新逻辑。
"""

from typing import Any, Dict, List, Optional

from config import STAT_MIN, STAT_MAX
from systems.state_machine import StateMachine
from world.map import GameMap
from world.time_system import TimeSystem

# NPC渲染颜色（与NPC_INITIAL_DATA顺序对应）
NPC_COLORS: list[tuple[int, int, int]] = [
    (255, 80, 80),     # 阿强 - 红
    (255, 180, 200),   # 阿珍 - 粉
    (80, 130, 255),    # 大壮 - 蓝
    (255, 200, 80),    # 小美 - 橙
    (180, 180, 180),   # 老李 - 灰
]


class NPC:
    """NPC角色类，管理属性和行为状态"""

    def __init__(self, data: Dict[str, Any],
                 time_system: TimeSystem, game_map: GameMap) -> None:
        self.name: str = data["name"]
        self.gender: str = data["gender"]
        self.x: int = data["x"]
        self.y: int = data["y"]
        self.hunger: float = float(data["hunger"])
        self.energy: float = float(data["energy"])
        self.mood: float = float(data["mood"])
        self.inventory: List[Any] = list(data.get("inventory", []))
        self._time: TimeSystem = time_system
        self._map: GameMap = game_map
        # 行走目标坐标
        self.target_x: Optional[int] = None
        self.target_y: Optional[int] = None
        # 行走目的（到达目标后切换到的状态）
        self._walk_purpose: str = "IDLE"
        # 空闲计时器
        self._idle_timer: int = 0
        # 移动冷却帧
        self._move_cooldown: int = 0
        # A*路径（步进列表）
        self._path: list[tuple[int, int]] = []

        # 状态机，初始为IDLE
        self.fsm: StateMachine = StateMachine(initial_state="IDLE")

    def update(self) -> None:
        """每帧更新：属性自然变化 + 状态机更新"""
        # hunger 每 tick +0.1
        self.hunger = min(STAT_MAX, self.hunger + 0.1)

        # energy 白天 -0.05/tick，夜晚 -0.02/tick
        if self._time.is_day():
            self.energy = max(STAT_MIN, self.energy - 0.05)
        else:
            self.energy = max(STAT_MIN, self.energy - 0.02)

        # 检查强制状态转换
        self._check_state_transitions()

        # 更新当前状态
        self.fsm.update(self)

    def _check_state_transitions(self) -> None:
        """检查并触发强制状态转换（生存优先级高于自由行为）"""
        current = self.fsm.get_current_state()

        # 最高优先级：能量不足 → SLEEP
        if self.energy < 20:
            if current != "SLEEP":
                self.fsm.set_state("SLEEP", self)
            return

        # 夜晚 → SLEEP
        if self._time.is_night():
            if current != "SLEEP":
                self.fsm.set_state("SLEEP", self)
            return

        # 从睡眠中醒来
        if current == "SLEEP":
            self.fsm.set_state("IDLE", self)
            return

        # 饥饿 → SEARCH_FOOD（不打断已开始的觅食或进食）
        if self.hunger > 70 and current not in ("SEARCH_FOOD", "EAT"):
            self.fsm.set_state("SEARCH_FOOD", self)
            return

    def get_state(self) -> str:
        """返回当前状态名称"""
        return self.fsm.get_current_state() or "IDLE"

    def get_sidebar_info(self) -> Dict[str, Any]:
        """返回侧边栏显示的摘要信息"""
        return {
            "name": self.name,
            "hunger": int(self.hunger),
            "energy": int(self.energy),
            "mood": int(self.mood),
            "state": self.get_state(),
        }
