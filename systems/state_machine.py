"""
通用有限状态机（FSM）框架 — Island Sim v1

提供State抽象基类和StateMachine管理器，支持状态注册、切换和更新。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class State(ABC):
    """状态抽象基类，所有具体状态需继承此类"""

    def enter(self, owner: Any) -> None:
        """进入状态时调用，子类可重写"""
        pass

    @abstractmethod
    def update(self, owner: Any) -> None:
        """每帧更新逻辑，子类必须实现"""
        ...

    def exit(self, owner: Any) -> None:
        """退出状态时调用，子类可重写"""
        pass


class StateMachine:
    """通用状态机管理器，管理状态注册、切换和更新"""

    def __init__(self, initial_state: Optional[str] = None) -> None:
        self._states: Dict[str, State] = {}
        self._current_state_name: Optional[str] = None
        self._previous_state_name: Optional[str] = None
        self._history: list[str] = []

        if initial_state:
            self._current_state_name = initial_state

    def add_state(self, name: str, state: State) -> None:
        """注册一个状态"""
        self._states[name] = state

    def set_state(self, name: str, owner: Any) -> None:
        """切换到指定状态，自动调用旧状态的exit和新状态的enter"""
        if name not in self._states:
            raise KeyError(f"状态 '{name}' 未注册")

        if self._current_state_name:
            self._states[self._current_state_name].exit(owner)
            self._previous_state_name = self._current_state_name

        self._current_state_name = name
        self._history.append(name)
        self._states[name].enter(owner)

    def update(self, owner: Any) -> None:
        """更新当前状态"""
        if self._current_state_name:
            self._states[self._current_state_name].update(owner)

    def get_current_state(self) -> Optional[str]:
        """获取当前状态名称"""
        return self._current_state_name

    @property
    def previous_state(self) -> Optional[str]:
        """获取上一个状态名称"""
        return self._previous_state_name

    @property
    def history(self) -> list[str]:
        """获取状态切换历史"""
        return self._history.copy()
