"""
长期压力追踪器 — Island Sim v1

统计饥饿平均值趋势、weakened比例、区域资源消耗速度和恢复速度。
数据来自真实运行统计数据，用于观察生态趋势（恶化/恢复）。
"""

from collections import deque
from typing import Any


class PressureTracker:
    """长期压力统计。跟踪生态趋势，不做预测。"""

    def __init__(self, window_size: int = 600) -> None:
        self._window_size = window_size
        self._hunger_readings: deque[float] = deque(maxlen=window_size)
        self._weakened_counts: deque[int] = deque(maxlen=window_size)
        self._npc_counts: deque[int] = deque(maxlen=window_size)
        self._depletion_rate: deque[int] = deque(maxlen=window_size)
        self._recovery_rate: deque[int] = deque(maxlen=window_size)
        self._readings_since_last_report: int = 0

    def record(
        self,
        tick: int,
        npcs: list,
        depletion_count: int,
        recovery_count: int,
    ) -> None:
        """记录一次压力数据点"""
        avg_hunger = sum(getattr(n, "hunger", 0) for n in npcs) / max(len(npcs), 1)
        weakened = sum(1 for n in npcs if getattr(n, "_weakened", False))

        self._hunger_readings.append(avg_hunger)
        self._weakened_counts.append(weakened)
        self._npc_counts.append(len(npcs))
        self._depletion_rate.append(depletion_count)
        self._recovery_rate.append(recovery_count)
        self._readings_since_last_report += 1

    def get_hunger_trend(self) -> dict[str, Any]:
        """饥饿平均值趋势"""
        if len(self._hunger_readings) < 2:
            return {"trend": "stable", "current": 0, "average": 0, "samples": 0}

        readings = list(self._hunger_readings)
        avg = sum(readings) / len(readings)
        first_half = sum(readings[:len(readings)//2]) / max(len(readings)//2, 1)
        second_half = sum(readings[len(readings)//2:]) / max(len(readings) - len(readings)//2, 1)

        if second_half > first_half * 1.1:
            trend = "rising"
        elif second_half < first_half * 0.9:
            trend = "falling"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "current": round(readings[-1], 1),
            "average": round(avg, 1),
            "min": round(min(readings), 1),
            "max": round(max(readings), 1),
            "samples": len(readings),
        }

    def get_weakened_trend(self) -> dict[str, Any]:
        """weakened NPC 比例趋势"""
        if not self._weakened_counts:
            return {"ratio": 0, "trend": "stable"}

        recent = list(self._weakened_counts)
        total_npc = list(self._npc_counts)
        ratios = [
            recent[i] / max(total_npc[i], 1)
            for i in range(len(recent))
        ]
        avg_ratio = sum(ratios) / len(ratios)

        if len(ratios) > 2:
            first = sum(ratios[:len(ratios)//2]) / max(len(ratios)//2, 1)
            second = sum(ratios[len(ratios)//2:]) / max(len(ratios) - len(ratios)//2, 1)
            trend = "rising" if second > first * 1.1 else (
                "falling" if second < first * 0.9 else "stable"
            )
        else:
            trend = "stable"

        return {
            "ratio": round(avg_ratio, 3),
            "trend": trend,
            "current_weakened": recent[-1] if recent else 0,
        }

    def get_resource_trend(self) -> dict[str, Any]:
        """资源消耗/恢复趋势"""
        depletions = list(self._depletion_rate) if self._depletion_rate else [0]
        recoveries = list(self._recovery_rate) if self._recovery_rate else [0]

        total_depletion = sum(depletions)
        total_recovery = sum(recoveries)

        return {
            "total_depletions": total_depletion,
            "total_recoveries": total_recovery,
            "net_change": total_recovery - total_depletion,
            "depletion_rate_per_tick": round(
                total_depletion / max(len(depletions), 1), 3,
            ),
            "recovery_rate_per_tick": round(
                total_recovery / max(len(recoveries), 1), 3,
            ),
        }

    def get_summary(self) -> dict[str, Any]:
        """获取完整压力摘要"""
        return {
            "hunger": self.get_hunger_trend(),
            "weakened": self.get_weakened_trend(),
            "resource": self.get_resource_trend(),
            "samples_since_last_report": self._readings_since_last_report,
        }
