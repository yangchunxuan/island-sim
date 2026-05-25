"""
NPC记忆系统（接口框架） — Island Sim v1

预留记忆功能接口，后续迭代实现复杂记忆逻辑。
"""

from typing import Any, Dict, List


class Memory:
    """NPC记忆系统（空壳）

    预留 add_memory / get_recent 接口供后续迭代使用。
    """

    def __init__(self) -> None:
        self._memories: List[Dict[str, Any]] = []

    def add_memory(self, event_type: str, content: Any) -> None:
        """记录一条记忆"""
        self._memories.append({"type": event_type, "content": content})

    def get_recent(self, count: int = 5) -> List[Dict[str, Any]]:
        """获取最近 count 条记忆"""
        return self._memories[-count:]
