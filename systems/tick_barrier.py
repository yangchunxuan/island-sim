"""
Strict Tick Barrier — Simulation OS 基础设施 (T-035)

保证每个 tick 内各系统串行执行，禁止并发写。
执行顺序：Geography → Ecology → Behavior → Validation
"""

from enum import Enum
from dataclasses import dataclass, field


class TickPhase(Enum):
    GEOGRAPHY = 'geography'      # pressure_map.update()
    ECOLOGY = 'ecology'          # resource_mgr.update()
    BEHAVIOR = 'behavior'        # npc.update() for each npc
    VALIDATION = 'validation'    # 预留（当前为空操作）


@dataclass
class TickResult:
    tick_number: int
    phases_completed: list  # list of TickPhase
    errors: list = field(default_factory=list)  # list of (TickPhase, Exception)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class TickBarrier:
    PHASE_ORDER = [TickPhase.GEOGRAPHY, TickPhase.ECOLOGY, TickPhase.BEHAVIOR, TickPhase.VALIDATION]

    def __init__(self, pressure_map, resource_mgr, npcs, time_system):
        self._pressure_map = pressure_map
        self._resource_mgr = resource_mgr
        self._npcs = npcs
        self._time_system = time_system
        self._tick_count = 0

    def execute_tick(self) -> TickResult:
        """
        严格串行执行一个完整tick:
        1. time_system.tick()
        2. GEOGRAPHY: pressure_map.update(resource_mgr, time_system)
        3. ECOLOGY: resource_mgr.update(time_system)
        4. BEHAVIOR: for npc in npcs: npc.update()
        5. VALIDATION: 预留（当前pass）

        如果某阶段抛异常，记录到errors但继续执行后续阶段
        """
        self._tick_count += 1
        tick_number = self._tick_count
        phases_completed = []
        errors = []

        # 1. time tick
        try:
            self._time_system.tick()
        except Exception as e:
            errors.append((TickPhase.GEOGRAPHY, e))
        # no phase recorded for time_system.tick()

        # 2. GEOGRAPHY
        try:
            self._pressure_map.update(self._resource_mgr, self._time_system)
            phases_completed.append(TickPhase.GEOGRAPHY)
        except Exception as e:
            errors.append((TickPhase.GEOGRAPHY, e))
            phases_completed.append(TickPhase.GEOGRAPHY)

        # 3. ECOLOGY
        try:
            self._resource_mgr.update(self._time_system)
            phases_completed.append(TickPhase.ECOLOGY)
        except Exception as e:
            errors.append((TickPhase.ECOLOGY, e))
            phases_completed.append(TickPhase.ECOLOGY)

        # 4. BEHAVIOR
        try:
            for npc in self._npcs:
                npc.update()
            phases_completed.append(TickPhase.BEHAVIOR)
        except Exception as e:
            errors.append((TickPhase.BEHAVIOR, e))
            phases_completed.append(TickPhase.BEHAVIOR)

        # 5. VALIDATION (预留, 空操作)
        phases_completed.append(TickPhase.VALIDATION)

        return TickResult(
            tick_number=tick_number,
            phases_completed=phases_completed,
            errors=errors,
        )

    def get_phase_order(self) -> list:
        return list(self.PHASE_ORDER)

    def run_days(self, days: int) -> list:
        """运行N天，返回所有TickResult列表"""
        return [self.execute_tick() for _ in range(days)]
