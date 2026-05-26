"""
季节系统测试 — Island Sim v1 (T-027)

验证：四季循环、季节名称、时间字符串格式。
"""

from config import DAY_TICKS, SEASON_ENERGY_COST, SEASON_FISH_BONUS, SEASON_MUSHROOM_BONUS
from world.time_system import TimeSystem


class TestSeasonCycle:
    """四季循环测试"""

    def test_initial_season(self):
        ts = TimeSystem()
        assert ts.get_season() == "spring"

    def test_season_transitions(self):
        ts = self._advance(30)
        assert ts.get_season() == "summer"
        ts = self._advance(30, ts)
        assert ts.get_season() == "autumn"
        ts = self._advance(30, ts)
        assert ts.get_season() == "winter"
        ts = self._advance(30, ts)
        assert ts.get_season() == "spring"

    def test_season_name(self):
        ts = TimeSystem()
        assert ts.get_season_name() == "春季"
        ts = self._advance(60, ts)
        assert "秋" in ts.get_season_name()

    def test_season_progress(self):
        ts = TimeSystem()
        assert 0.0 <= ts.get_season_progress() < 1.0

    def test_time_string_includes_season(self):
        ts = TimeSystem()
        s = ts.get_time_string()
        assert "Day" in s
        assert ("春" in s or "夏" in s or "秋" in s or "冬" in s)

    @staticmethod
    def _advance(days: int, ts=None):
        if ts is None:
            ts = TimeSystem()
        for _ in range(days * DAY_TICKS):
            ts.tick()
        return ts


class TestSeasonEffects:
    """季节对资源的影响测试"""

    def test_mushroom_bonus_varied(self):
        assert SEASON_MUSHROOM_BONUS["spring"] > SEASON_MUSHROOM_BONUS["winter"]

    def test_fish_bonus_peak_summer(self):
        assert SEASON_FISH_BONUS["summer"] > SEASON_FISH_BONUS["winter"]

    def test_energy_cost_highest_winter(self):
        assert SEASON_ENERGY_COST["winter"] > SEASON_ENERGY_COST["summer"]
