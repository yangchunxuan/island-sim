"""
时间系统模块 — Island Sim v1

管理游戏内时间流逝、昼夜判断、天数计算。
每个 game tick 推进时间，时间流速由 config.DAY_TICKS 控制。
"""

from config import DAY_TICKS


class TimeSystem:
    """游戏内时间系统"""

    DAY_START: int = 6
    """白天开始小时"""
    NIGHT_START: int = 20
    """夜晚开始小时"""

    def __init__(self) -> None:
        self._tick_count: int = 0

    def tick(self) -> None:
        """推进一个 game tick 的时间"""
        self._tick_count += 1

    def get_hour(self) -> float:
        """返回当前游戏小时 (0.0 ~ 24.0)"""
        return (24.0 * self._tick_count) / DAY_TICKS % 24.0

    def is_day(self) -> bool:
        """判断当前是否为白天 (hour 6-20)"""
        return self.DAY_START <= self.get_hour() < self.NIGHT_START

    def is_night(self) -> bool:
        """判断当前是否为夜晚 (hour 20-6)"""
        return not self.is_day()

    def get_day_count(self) -> int:
        """返回已经过的完整天数"""
        return self._tick_count // DAY_TICKS

    def get_time_string(self) -> str:
        """返回 'Day X, HH:MM' 格式的时间字符串"""
        hour = self.get_hour()
        hh = int(hour)
        mm = int((hour - hh) * 60)
        return f"Day {self.get_day_count()}, {hh:02d}:{mm:02d}"
