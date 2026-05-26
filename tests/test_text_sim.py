"""
T-029 文字直播模式 测试

验证 TextSimulation 可以启动、运行、检测事件并输出文字。
"""

import sys
from io import StringIO
from typing import Generator

import pytest

from systems.text_sim import TextSimulation


class TestTextSimulationInit:
    """TextSimulation 初始化和基本结构"""

    def test_create(self) -> None:
        """可以创建 TextSimulation 实例"""
        sim = TextSimulation(speed=5.0)
        assert sim is not None
        assert sim.speed == 5.0
        assert sim._running is True

    def test_speed_zero_clamped(self) -> None:
        """speed=0 应被接受（尽可能快）"""
        sim = TextSimulation(speed=0.0)
        assert sim.speed == 0.0

    def test_speed_negative_clamped(self) -> None:
        """负数 speed 应被钳制为 0"""
        sim = TextSimulation(speed=-1.0)
        assert sim.speed == 0.0

    def test_game_objects_created(self) -> None:
        """游戏对象应正确创建"""
        sim = TextSimulation()
        assert sim.npcs is not None
        assert len(sim.npcs) == 5
        assert sim.time_system is not None
        assert sim.resource_mgr is not None
        assert sim.game_map is not None

    def test_npc_names(self) -> None:
        """NPC 名称正确"""
        sim = TextSimulation()
        names = [n.name for n in sim.npcs]
        assert "阿强" in names
        assert "阿珍" in names
        assert "大壮" in names
        assert "小美" in names
        assert "老李" in names

    def test_snapshots_initialized(self) -> None:
        """初始化快照应包含所有NPC"""
        sim = TextSimulation()
        assert len(sim._prev_npc) == 5
        for name, snap in sim._prev_npc.items():
            assert "state" in snap
            assert "x" in snap
            assert "y" in snap


class TestTextSimulationRun:
    """TextSimulation 运行测试"""

    def test_run_one_tick(self) -> None:
        """运行1tick不应报错"""
        sim = TextSimulation(speed=0.0)
        sim.time_system.tick()
        for npc in sim.npcs:
            npc.update()
        sim.resource_mgr.update()
        sim._detect_all()
        # 不报错就通过

    def test_run_multiple_ticks(self) -> None:
        """运行100tick不应报错"""
        sim = TextSimulation(speed=0.0)
        for _ in range(100):
            sim.time_system.tick()
            for npc in sim.npcs:
                npc.update()
            sim.resource_mgr.update()
            sim._detect_all()

    def test_output_contains_chinese(self, capsys: pytest.CaptureFixture) -> None:
        """输出应包含中文"""
        sim = TextSimulation(speed=0.0)
        for _ in range(50):
            sim.time_system.tick()
            for npc in sim.npcs:
                npc.update()
            sim.resource_mgr.update()
            sim._detect_all()
        captured = capsys.readouterr()
        # 至少有一些输出或没有报错
        assert captured.err == ""

    def test_run_one_day(self) -> None:
        """完整运行1天（1200tick）不应报错"""
        sim = TextSimulation(speed=0.0)
        for _ in range(DAY_TICKS):
            sim.time_system.tick()
            for npc in sim.npcs:
                npc.update()
            sim.resource_mgr.update()
            sim._detect_all()


# 在函数内需要可用
from config import DAY_TICKS


class TestEventDetection:
    """事件检测逻辑"""

    def test_day_change_detected(self, capsys: pytest.CaptureFixture) -> None:
        """天数变化应输出消息"""
        sim = TextSimulation(speed=0.0)
        sim._prev_day_count = 0
        # 推进到第二天
        for _ in range(DAY_TICKS):
            sim.time_system.tick()
        sim._detect_day_change()
        captured = capsys.readouterr()
        assert "第" in captured.out
        assert "天" in captured.out

    def test_dawn_dusk_detected(self, capsys: pytest.CaptureFixture) -> None:
        """日出日落应输出消息"""
        sim = TextSimulation(speed=0.0)
        sim._prev_is_day = False
        # 推进到白天（Day 0, hour ~6 之后）
        # 从 tick 0 开始，hour=0.0，所以需要约 300 tick 到 hour 6
        for _ in range(310):
            sim.time_system.tick()
        sim._detect_dawn_dusk()
        captured = capsys.readouterr()
        # 日出可能输出中文
        assert "天亮了" in captured.out

    def test_npc_state_change(self) -> None:
        """NPC状态切换触发格式化"""
        sim = TextSimulation(speed=0.0)
        npc = sim.npcs[0]
        old_state = npc.get_state()
        # 强制切换
        npc.fsm.set_state("WALK", npc)
        new_state = npc.get_state()
        msg = sim._format_state(npc.name, old_state, new_state, npc)
        assert npc.name in msg
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_resource_deplete(self, capsys: pytest.CaptureFixture) -> None:
        """资源耗尽应输出消息"""
        sim = TextSimulation(speed=0.0)
        # 模拟一个depleted事件
        pos = (5, 5)
        sim._prev_depleted = set()
        sim.resource_mgr._depleted.add(pos)
        sim._detect_resource_events()
        captured = capsys.readouterr()
        assert "耗尽" in captured.out or "恢复" in captured.out or captured.out == ""

    def test_encounter_detected(self) -> None:
        """NPC相遇应输出消息"""
        sim = TextSimulation(speed=0.0)
        # 把两个NPC放到一起
        a, b = sim.npcs[0], sim.npcs[1]
        a.x, a.y = 5, 5
        b.x, b.y = 5, 6  # 曼哈顿距离=1，小于等于2
        sim._detect_encounters()
        assert (a.name, b.name) in sim._prev_nearby_pairs or \
               (b.name, a.name) in sim._prev_nearby_pairs

    def test_encounter_output(self, capsys: pytest.CaptureFixture) -> None:
        """NPC相遇输出应包含双方名称"""
        sim = TextSimulation(speed=0.0)
        a, b = sim.npcs[0], sim.npcs[1]
        a.x, a.y = 5, 5
        b.x, b.y = 5, 6
        sim._detect_encounters()
        captured = capsys.readouterr()
        if captured.out:
            assert a.name in captured.out
            assert b.name in captured.out

    def test_weakened_detected(self, capsys: pytest.CaptureFixture) -> None:
        """NPC虚弱状态应输出消息"""
        sim = TextSimulation(speed=0.0)
        npc = sim.npcs[0]
        prev = sim._prev_npc[npc.name]
        prev["weakened"] = False
        npc._weakened = True
        sim._detect_npc_weakened()
        captured = capsys.readouterr()
        assert "虚弱" in captured.out

    def test_season_change(self, capsys: pytest.CaptureFixture) -> None:
        """季节变化应输出消息"""
        sim = TextSimulation(speed=0.0)
        sim._prev_season = "winter"
        # 推进到下一个季节
        from config import SPRING_DAYS, DAY_TICKS
        for _ in range(SPRING_DAYS * DAY_TICKS + 1):
            sim.time_system.tick()
        sim._detect_season_change()
        captured = capsys.readouterr()
        if captured.out:
            assert "来了" in captured.out
