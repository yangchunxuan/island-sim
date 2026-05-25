"""
FSM状态机单元测试 — Island Sim v1

覆盖：状态注册、切换、回调、异常。
"""

import pytest
from systems.state_machine import State, StateMachine


# ── 测试用状态实现 ──

class IdleState(State):
    """测试用IDLE状态"""

    def enter(self, owner) -> None:
        owner.log.append("enter_idle")

    def update(self, owner) -> None:
        owner.log.append("update_idle")

    def exit(self, owner) -> None:
        owner.log.append("exit_idle")


class WalkState(State):
    """测试用WALK状态"""

    def enter(self, owner) -> None:
        owner.log.append("enter_walk")

    def update(self, owner) -> None:
        owner.log.append("update_walk")

    def exit(self, owner) -> None:
        owner.log.append("exit_walk")


class DummyOwner:
    """模拟状态持有者，记录回调日志"""
    def __init__(self) -> None:
        self.log: list[str] = []


# ── 测试用例 ──

class TestStateMachine:
    """状态机功能测试"""

    def test_add_state(self) -> None:
        """注册状态后不应报错"""
        fsm = StateMachine()
        fsm.add_state("IDLE", IdleState())
        assert fsm.get_current_state() is None

    def test_initial_state(self) -> None:
        """构造函数可设置初始状态"""
        fsm = StateMachine(initial_state="IDLE")
        assert fsm.get_current_state() == "IDLE"

    def test_set_state_triggers_enter(self) -> None:
        """切换到状态时触发enter回调"""
        fsm = StateMachine()
        fsm.add_state("IDLE", IdleState())
        owner = DummyOwner()
        fsm.set_state("IDLE", owner)
        assert owner.log == ["enter_idle"]

    def test_transition_triggers_exit_and_enter(self) -> None:
        """状态切换时自动调用旧状态的exit和新状态的enter"""
        fsm = StateMachine()
        fsm.add_state("IDLE", IdleState())
        fsm.add_state("WALK", WalkState())
        owner = DummyOwner()
        fsm.set_state("IDLE", owner)
        owner.log.clear()
        fsm.set_state("WALK", owner)
        assert "exit_idle" in owner.log
        assert "enter_walk" in owner.log

    def test_update_calls_current_state(self) -> None:
        """update()仅调用当前状态的update"""
        fsm = StateMachine()
        fsm.add_state("IDLE", IdleState())
        owner = DummyOwner()
        fsm.set_state("IDLE", owner)
        owner.log.clear()
        fsm.update(owner)
        assert owner.log == ["update_idle"]

    def test_get_current_state(self) -> None:
        """get_current_state()返回当前状态名"""
        fsm = StateMachine()
        fsm.add_state("IDLE", IdleState())
        owner = DummyOwner()
        fsm.set_state("IDLE", owner)
        assert fsm.get_current_state() == "IDLE"

    def test_previous_state(self) -> None:
        """previous_state记录上一个状态"""
        fsm = StateMachine()
        fsm.add_state("IDLE", IdleState())
        fsm.add_state("WALK", WalkState())
        owner = DummyOwner()
        fsm.set_state("IDLE", owner)
        fsm.set_state("WALK", owner)
        assert fsm.previous_state == "IDLE"

    def test_history(self) -> None:
        """history记录所有状态切换路径"""
        fsm = StateMachine()
        fsm.add_state("IDLE", IdleState())
        fsm.add_state("WALK", WalkState())
        owner = DummyOwner()
        fsm.set_state("IDLE", owner)
        fsm.set_state("WALK", owner)
        assert fsm.history == ["IDLE", "WALK"]

    def test_set_unregistered_state_raises(self) -> None:
        """切换到未注册状态应抛KeyError"""
        fsm = StateMachine()
        owner = DummyOwner()
        with pytest.raises(KeyError):
            fsm.set_state("UNKNOWN", owner)

    def test_state_must_implement_update(self) -> None:
        """未实现update的State子类不能实例化"""
        class BadState(State):
            pass
        with pytest.raises(TypeError):
            BadState()

    def test_history_isolation(self) -> None:
        """history返回副本，外部修改不影响内部"""
        fsm = StateMachine()
        fsm.add_state("IDLE", IdleState())
        owner = DummyOwner()
        fsm.set_state("IDLE", owner)
        hist = fsm.history
        hist.append("WALK")
        assert fsm.history == ["IDLE"]

    def test_update_without_state(self) -> None:
        """未设置状态时update不报错"""
        fsm = StateMachine()
        owner = DummyOwner()
        # 不应抛出异常
        fsm.update(owner)
