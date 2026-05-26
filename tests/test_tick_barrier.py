"""Tests for Strict Tick Barrier (T-035)"""

from unittest.mock import MagicMock, call

from systems.tick_barrier import TickPhase, TickResult, TickBarrier


def make_mocks():
    mock_time = MagicMock()
    mock_pressure = MagicMock()
    mock_resource = MagicMock()
    mock_npcs = [MagicMock(), MagicMock()]
    return mock_time, mock_pressure, mock_resource, mock_npcs


class TestTickBarrier:
    def test_execute_tick_order(self):
        """验证调用顺序: time.tick → pressure.update → resource.update → npc.update"""
        mock_time, mock_pressure, mock_resource, mock_npcs = make_mocks()
        barrier = TickBarrier(mock_pressure, mock_resource, mock_npcs, mock_time)

        result = barrier.execute_tick()

        assert result.success is True
        # time_system.tick() called first
        mock_time.tick.assert_called_once()
        # then pressure_map.update(resource_mgr, time_system)
        mock_pressure.update.assert_called_once_with(mock_resource, mock_time)
        # then resource_mgr.update(time_system)
        mock_resource.update.assert_called_once_with(mock_time)
        # then each npc.update()
        for npc in mock_npcs:
            npc.update.assert_called_once()

    def test_phase_error_continues(self):
        """mock某阶段抛异常，验证后续阶段仍执行"""
        mock_time, mock_pressure, mock_resource, mock_npcs = make_mocks()
        # resource_mgr.update raises
        mock_resource.update.side_effect = ValueError("resource error")
        barrier = TickBarrier(mock_pressure, mock_resource, mock_npcs, mock_time)

        result = barrier.execute_tick()

        # pressure.update should still have been called (before the error)
        mock_pressure.update.assert_called_once()
        # resource.update was called (and raised)
        mock_resource.update.assert_called_once()
        # npcs should still have been updated (BEHAVIOR phase continues)
        for npc in mock_npcs:
            npc.update.assert_called_once()
        # time.tick should have been called
        mock_time.tick.assert_called_once()

        assert result.success is False
        assert len(result.errors) == 1
        phase, exc = result.errors[0]
        assert phase == TickPhase.ECOLOGY
        assert isinstance(exc, ValueError)

    def test_tick_result_success(self):
        """正常tick的result.success == True"""
        mock_time, mock_pressure, mock_resource, mock_npcs = make_mocks()
        barrier = TickBarrier(mock_pressure, mock_resource, mock_npcs, mock_time)

        result = barrier.execute_tick()

        assert result.success is True
        assert len(result.errors) == 0
        assert result.phases_completed == [
            TickPhase.GEOGRAPHY,
            TickPhase.ECOLOGY,
            TickPhase.BEHAVIOR,
            TickPhase.VALIDATION,
        ]

    def test_tick_result_with_error(self):
        """有错误的result.success == False, errors非空"""
        mock_time, mock_pressure, mock_resource, mock_npcs = make_mocks()
        mock_pressure.update.side_effect = RuntimeError("pressure failed")
        barrier = TickBarrier(mock_pressure, mock_resource, mock_npcs, mock_time)

        result = barrier.execute_tick()

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0][0] == TickPhase.GEOGRAPHY
        assert isinstance(result.errors[0][1], RuntimeError)

    def test_get_phase_order(self):
        """返回正确的4个phase顺序"""
        mock_time, mock_pressure, mock_resource, mock_npcs = make_mocks()
        barrier = TickBarrier(mock_pressure, mock_resource, mock_npcs, mock_time)

        order = barrier.get_phase_order()

        assert order == [
            TickPhase.GEOGRAPHY,
            TickPhase.ECOLOGY,
            TickPhase.BEHAVIOR,
            TickPhase.VALIDATION,
        ]

    def test_run_days(self):
        """运行N天返回正确数量的TickResult"""
        mock_time, mock_pressure, mock_resource, mock_npcs = make_mocks()
        barrier = TickBarrier(mock_pressure, mock_resource, mock_npcs, mock_time)

        results = barrier.run_days(3)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert [r.tick_number for r in results] == [1, 2, 3]

    def test_tick_count_increments(self):
        """多次execute_tick后tick_count正确"""
        mock_time, mock_pressure, mock_resource, mock_npcs = make_mocks()
        barrier = TickBarrier(mock_pressure, mock_resource, mock_npcs, mock_time)

        r1 = barrier.execute_tick()
        r2 = barrier.execute_tick()
        r3 = barrier.execute_tick()

        assert r1.tick_number == 1
        assert r2.tick_number == 2
        assert r3.tick_number == 3
        assert r1.success is True
        assert r2.success is True
        assert r3.success is True
