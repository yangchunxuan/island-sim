"""
时间系统测试 — Island Sim v1

测试 TimeSystem 的时间推进、昼夜切换、天数计算。
"""

from world.time_system import TimeSystem
from config import DAY_TICKS


class TestTimeSystem:
    """TimeSystem 单元测试"""

    def test_initial_time(self) -> None:
        """初始状态：第0天，hour=0"""
        ts = TimeSystem()
        assert ts.get_day_count() == 0
        assert ts.get_hour() == 0.0
        assert ts.get_time_string() == "Day 0, 00:00"

    def test_tick_advances_hour(self) -> None:
        """每次 tick 推进时间"""
        ts = TimeSystem()
        ts.tick()
        expected_hour = 24.0 / DAY_TICKS
        assert abs(ts.get_hour() - expected_hour) < 1e-9

    def test_day_cycle(self) -> None:
        """经过 DAY_TICKS 个 tick 后回到第1天 hour=0"""
        ts = TimeSystem()
        for _ in range(DAY_TICKS):
            ts.tick()
        assert ts.get_day_count() == 1
        assert abs(ts.get_hour() - 0.0) < 1e-9
        assert ts.get_time_string() == "Day 1, 00:00"

    def test_multiple_days(self) -> None:
        """多个完整天的循环"""
        ts = TimeSystem()
        days = 5
        for _ in range(days * DAY_TICKS):
            ts.tick()
        assert ts.get_day_count() == days

    def test_day_time(self) -> None:
        """hour=6~20 为白天"""
        ts = TimeSystem()
        # 推进到 hour=12（正午），应在白天
        target_ticks = int(12 * DAY_TICKS / 24)
        for _ in range(target_ticks):
            ts.tick()
        assert ts.is_day()
        assert not ts.is_night()

    def test_night_time_after_20(self) -> None:
        """hour=20~24 为夜晚"""
        ts = TimeSystem()
        # 推进到 hour=22
        target_ticks = int(22 * DAY_TICKS / 24)
        for _ in range(target_ticks):
            ts.tick()
        assert ts.is_night()
        assert not ts.is_day()

    def test_night_time_before_6(self) -> None:
        """hour=0~6 为夜晚"""
        ts = TimeSystem()
        # 推进到 hour=3
        target_ticks = int(3 * DAY_TICKS / 24)
        for _ in range(target_ticks):
            ts.tick()
        assert ts.is_night()
        assert not ts.is_day()

    def test_day_night_boundary(self) -> None:
        """hour=6 和 hour=20 为昼夜分界"""
        ts = TimeSystem()
        # hour=6 刚好为白天开始
        target_ticks = int(6 * DAY_TICKS / 24)
        for _ in range(target_ticks):
            ts.tick()
        assert ts.is_day()
        assert not ts.is_night()

        # hour=20 刚好为夜晚开始
        target_ticks = int(20 * DAY_TICKS / 24)
        ts2 = TimeSystem()
        for _ in range(target_ticks):
            ts2.tick()
        assert ts2.is_night()
        assert not ts2.is_day()

    def test_time_string_format(self) -> None:
        """验证 get_time_string 返回格式"""
        ts = TimeSystem()
        # 推进 1/4 天 = 6小时
        target_ticks = DAY_TICKS // 4
        for _ in range(target_ticks):
            ts.tick()
        assert ts.get_time_string() == "Day 0, 06:00"
