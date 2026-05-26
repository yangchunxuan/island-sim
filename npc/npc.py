"""
NPC角色模块 — Island Sim v1

定义NPC类，管理属性、状态机和每帧更新逻辑。
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from npc.ai_brain import AIBrain

from config import (
    FEAR_DECAY_RATE,
    FEAR_HUNGER_THRESHOLD,
    FEAR_INCREASE_RATE,
    FEAR_MAX,
    HUNGER_MOOD_DECAY_RATE,
    NPC_BEHAVIOR_TRAITS,
    STAT_MAX,
    STAT_MIN,
    WEAKENED_HUNGER_THRESHOLD,
    WEAKENED_RECOVERY_THRESHOLD,
    WEAKENED_TRIGGER_DURATION,
)
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

    _all_npcs: list["NPC"] = []

    @classmethod
    def set_all_npcs(cls, npcs: list["NPC"]) -> None:
        """设置所有NPC引用（创建完所有NPC后由main.py调用）"""
        cls._all_npcs = list(npcs)

    def __init__(self, data: Dict[str, Any],
                 time_system: TimeSystem, game_map: GameMap,
                 resource_mgr: Any = None,
                 ai_brain: Optional["AIBrain"] = None) -> None:
        self.name: str = data["name"]
        self.gender: str = data["gender"]
        self.x: int = data["x"]
        self.y: int = data["y"]
        self.hunger: float = float(data["hunger"])
        self.energy: float = float(data["energy"])
        self.mood: float = float(data["mood"])
        self.inventory: List[Any] = list(data.get("inventory", []))
        # ── T-020 行为倾向（支持data覆盖用于测试）──
        config_traits = NPC_BEHAVIOR_TRAITS.get(self.name, {})
        self.risk_tolerance: float = float(data.get("risk_tolerance", config_traits.get("risk_tolerance", 0.5)))
        """冒险倾向 0(保守)~1(冒险)"""
        self.laziness: float = float(data.get("laziness", config_traits.get("laziness", 0.5)))
        """懒惰程度 0(勤快)~1(懒惰)"""
        self.food_preference: float = float(data.get("food_preference", config_traits.get("food_preference", 0.5)))
        """食物偏好 0(森林)~1(水产/蘑菇)"""
        self.exploration_bias: float = float(data.get("exploration_bias", config_traits.get("exploration_bias", 0.5)))
        """探索倾向 0(恋家)~1(爱探索)"""
        self._time: TimeSystem = time_system
        self._map: GameMap = game_map
        self._resource_mgr: Any = resource_mgr
        # ── T-028 AI决策层 ──
        self._ai_brain: Optional["AIBrain"] = ai_brain
        """AI决策大脑引用（None表示不使用AI）"""
        self._ai_idle_frames: int = 0
        """连续空闲帧数，超1800帧(30秒)触发AI长期规划"""
        # ── FR-002 恐惧系统 ──
        self.fear: float = 0.0
        """恐惧值 0(冷静)~1(恐慌)，受饥饿影响"""

        self._prev_mood: float = self.mood
        """上一帧mood值，用于检测重大情绪波动"""
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
        # Weakened系统：长时间高hunger导致效率下降
        self._weakened: bool = False
        self._hunger_high_duration: int = 0  # hunger超过阈值的连续帧数

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

        # 高hunger导致mood缓慢下降
        if self.hunger > 60:
            self.mood = max(STAT_MIN, self.mood - HUNGER_MOOD_DECAY_RATE)

        # ── FR-002 恐惧系统：饥饿影响恐惧值 ──
        if self.hunger > FEAR_HUNGER_THRESHOLD:
            self.fear = min(FEAR_MAX, self.fear + FEAR_INCREASE_RATE)
        elif self.hunger < FEAR_HUNGER_THRESHOLD:
            self.fear = max(0.0, self.fear - FEAR_DECAY_RATE)

        # 更新weakened状态
        self._update_weakened()

        # ── T-028 AI决策：重大事件检查 ──
        self._check_ai_events()

        # 检查强制状态转换
        self._check_state_transitions()

        # 更新当前状态
        self.fsm.update(self)

    def _update_weakened(self) -> None:
        """跟踪持续高hunger时间，触发/解除weakened状态"""
        if self.hunger > WEAKENED_HUNGER_THRESHOLD:
            self._hunger_high_duration += 1
            if self._hunger_high_duration >= WEAKENED_TRIGGER_DURATION and not self._weakened:
                self._weakened = True
                print(f"[NPC] {self.name} became weakened")
        else:
            self._hunger_high_duration = max(
                0, self._hunger_high_duration - 2
            )
            if self.hunger <= WEAKENED_RECOVERY_THRESHOLD and self._weakened:
                self._weakened = False
                print(f"[NPC] {self.name} recovered from weakened")

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

    def _check_ai_events(self) -> None:
        """检测重大事件并触发AI情绪决策（非阻塞）"""
        if self._ai_brain is None:
            self._prev_mood = self.mood
            return

        # 心情暴跌 > 20点
        mood_drop = self._prev_mood - self.mood
        if mood_drop > 20:
            event = f"心情突然暴跌{mood_drop:.0f}点（从{self._prev_mood:.0f}到{self.mood:.0f}）"
            if self._ai_brain.should_query(self.name):
                self._ai_brain.request_decision(self, {"event": event})

        # 进入weakened状态
        if self._weakened and self._hunger_high_duration == WEAKENED_TRIGGER_DURATION:
            if self._ai_brain.should_query(self.name):
                self._ai_brain.request_decision(self, {"event": "进入了weakened虚弱状态"})

        self._prev_mood = self.mood

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
            "fear": int(self.fear * 100),
            "state": self.get_state(),
        }
