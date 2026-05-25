"""
世界观察者 — Island Sim v1

统一观察入口。每帧轮询游戏状态，检测变化并记录事件。
"""

from typing import Any, Optional

from observer.event_logger import EventLogger
from observer.long_term_memory import LongTermMemory
from observer.pattern_analyzer import PatternAnalyzer
from observer.narrative_generator import NarrativeGenerator


def _region_name(x: int, y: int) -> str:
    """将坐标映射到地理区域名称"""
    if x < 10 and y < 10:
        return "西北"
    if x >= 10 and y < 10:
        return "东北"
    if x < 10 and y >= 10:
        return "西南"
    return "东南"


class WorldObserver:
    """世界观察者。轮询状态、检测变化、记录事件、分析模式、生成叙事。"""

    ANALYSIS_INTERVAL: int = 1200  # 每1200tick分析一次

    def __init__(self) -> None:
        self.event_logger = EventLogger()
        self._analyzer = PatternAnalyzer(self.event_logger)
        self._narrator = NarrativeGenerator()
        self._prev_npc_state: dict[int, dict[str, Any]] = {}
        self._prev_depleted: set[tuple[int, int]] = set()
        self._prev_mushrooms: dict[tuple[int, int], int] = {}
        self._prev_fish: dict[tuple[int, int], int] = {}
        self._last_analysis_tick: int = 0
        self._last_report: Optional[dict[str, Any]] = None
        self._pressure_map: object = None
        self._memory: LongTermMemory = LongTermMemory()

    def set_pressure_map(self, pressure_map: object) -> None:
        """注入区域压力图引用"""
        self._pressure_map = pressure_map

    def _log_npc_profiles(self, tick: int, npcs: list) -> None:
        """记录每个NPC的行为倾向配置（首次检测时记录一次）"""
        if not hasattr(self, '_profile_logged'):
            self._profile_logged = set()
        for npc in npcs:
            name = getattr(npc, "name", "Unknown")
            if name in self._profile_logged:
                continue
            self._profile_logged.add(name)
            self.event_logger.log(
                tick, "NPC_BEHAVIOR_PROFILE",
                npc=name,
                details={
                    "risk_tolerance": round(getattr(npc, "risk_tolerance", 0.5), 2),
                    "laziness": round(getattr(npc, "laziness", 0.5), 2),
                    "food_preference": round(getattr(npc, "food_preference", 0.5), 2),
                    "exploration_bias": round(getattr(npc, "exploration_bias", 0.5), 2),
                },
            )

    def update(
        self,
        tick: int,
        resource_mgr: object,
        npcs: list,
    ) -> None:
        """主更新入口：检测变化 → 记录事件 → 定期分析"""
        self._log_npc_profiles(tick, npcs)
        if resource_mgr is not None:
            self._detect_resource_events(tick, resource_mgr)
        self._detect_npc_events(tick, npcs)

        # 区域压力事件
        pm = self._pressure_map
        if pm is not None and resource_mgr is not None:
            for ev_type, region in pm.update(tick, resource_mgr):
                self.event_logger.log(tick, ev_type, position=region)

        if resource_mgr is not None:
            self._update_resource_snapshot(resource_mgr)
        self._update_npc_snapshot(npcs)

        if tick - self._last_analysis_tick >= self.ANALYSIS_INTERVAL and tick > 0:
            self._last_analysis_tick = tick
            self._run_analysis(tick, npcs, resource_mgr)

    def _run_analysis(
        self,
        tick: int,
        npcs: list,
        resource_mgr: object,
    ) -> None:
        """执行模式分析和叙事生成，同时更新长期记忆"""
        report = self._analyzer.analyze(tick, npcs, resource_mgr)
        self._memory.update(tick, npcs, self._pressure_map)
        report["world_history"] = self._memory.get_summary()
        self._last_report = report
        self._narrator.generate(tick, report)

    # ── 资源事件检测 ──

    def _detect_resource_events(
        self,
        tick: int,
        resource_mgr: object,
    ) -> None:
        """轮询资源管理器，检测资源变化"""
        current_depleted = set(resource_mgr.depleted_forests)
        current_mushrooms = dict(resource_mgr.mushrooms)
        current_fish = dict(resource_mgr.fish)

        # 森林恢复
        recovered = self._prev_depleted - current_depleted
        for pos in recovered:
            self.event_logger.log(
                tick, "FOREST_RECOVERED",
                position=pos,
                details={"from": "depleted", "to": "active"},
            )

        # 资源耗尽
        newly_depleted = current_depleted - self._prev_depleted
        for pos in newly_depleted:
            self.event_logger.log(
                tick, "RESOURCE_DEPLETED",
                position=pos,
                details={"type": "forest"},
            )

        # 蘑菇生成
        for pos in current_mushrooms:
            if pos not in self._prev_mushrooms:
                self.event_logger.log(
                    tick, "MUSHROOM_SPAWN",
                    position=pos,
                    details=current_mushrooms[pos],
                )

        # 鱼生成
        for pos in current_fish:
            if pos not in self._prev_fish:
                self.event_logger.log(
                    tick, "FISH_SPAWN",
                    position=pos,
                    details=current_fish[pos],
                )

    # ── NPC事件检测 ──

    def _detect_npc_events(self, tick: int, npcs: list) -> None:
        """轮询NPC状态，检测行为变化"""
        for idx, npc in enumerate(npcs):
            prev = self._prev_npc_state.get(idx, {})
            current_state = npc.get_state()
            current_x = int(getattr(npc, "x", 0))
            current_y = int(getattr(npc, "y", 0))
            current_weakened = bool(getattr(npc, "_weakened", False))
            current_hunger = int(getattr(npc, "hunger", 0))
            name = getattr(npc, "name", "Unknown")

            # 首次记录跳过（无prev数据）
            if not prev:
                self._prev_npc_state[idx] = {
                    "state": current_state,
                    "x": current_x,
                    "y": current_y,
                    "weakened": current_weakened,
                    "hunger": current_hunger,
                }
                continue

            # Weakened状态变化
            if current_weakened and not prev.get("weakened"):
                self.event_logger.log(
                    tick, "NPC_ENTER_WEAKENED",
                    npc=name,
                    position=(current_x, current_y),
                    details={"hunger": current_hunger},
                )
            elif not current_weakened and prev.get("weakened"):
                self.event_logger.log(
                    tick, "NPC_RECOVER_WEAKENED",
                    npc=name,
                    position=(current_x, current_y),
                    details={"hunger": current_hunger},
                )

            # 饮食事件：状态从EAT切换到其他
            if prev.get("state") == "EAT" and current_state != "EAT":
                hunger_drop = prev.get("hunger", current_hunger) - current_hunger
                if hunger_drop > 0:
                    self.event_logger.log(
                        tick, "NPC_EAT",
                        npc=name,
                        position=(current_x, current_y),
                        details={"hunger_drop": hunger_drop},
                    )

            # 睡眠事件：状态进入SLEEP
            if current_state == "SLEEP" and prev.get("state") != "SLEEP":
                self.event_logger.log(
                    tick, "NPC_SLEEP",
                    npc=name,
                    position=(current_x, current_y),
                    details={"energy": int(getattr(npc, "energy", 0))},
                )

            # 区域移动
            prev_x, prev_y = prev.get("x", current_x), prev.get("y", current_y)
            prev_region = _region_name(prev_x, prev_y)
            curr_region = _region_name(current_x, current_y)
            if prev_region != curr_region:
                self.event_logger.log(
                    tick, "NPC_MOVE_REGION",
                    npc=name,
                    position=(current_x, current_y),
                    details={"from": prev_region, "to": curr_region},
                )

    # ── 快照更新 ──

    def _update_resource_snapshot(
        self,
        resource_mgr: object,
    ) -> None:
        """更新资源快照"""
        self._prev_depleted = set(resource_mgr.depleted_forests)
        self._prev_mushrooms = dict(resource_mgr.mushrooms)
        self._prev_fish = dict(resource_mgr.fish)

    def _update_npc_snapshot(
        self,
        npcs: list,
    ) -> None:
        """更新NPC快照"""
        for idx, npc in enumerate(npcs):
            self._prev_npc_state[idx] = {
                "state": npc.get_state(),
                "x": int(getattr(npc, "x", 0)),
                "y": int(getattr(npc, "y", 0)),
                "weakened": bool(getattr(npc, "_weakened", False)),
                "hunger": int(getattr(npc, "hunger", 0)),
            }

    @property
    def last_report(self) -> Optional[dict[str, Any]]:
        """返回最近一次分析报告"""
        return self._last_report
