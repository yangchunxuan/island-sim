"""
NPC关系系统（接口框架） — Island Sim v1

预留NPC间关系管理接口，后续迭代实现。
"""

from typing import Dict


class RelationshipSystem:
    """NPC关系系统（空壳）

    预留 set / get 接口供后续迭代使用。
    """

    def __init__(self) -> None:
        self._relationships: Dict[str, Dict[str, int]] = {}

    def set_relationship(self, npc_a: str, npc_b: str, value: int) -> None:
        """设置两个NPC间的关系值"""
        if npc_a not in self._relationships:
            self._relationships[npc_a] = {}
        self._relationships[npc_a][npc_b] = value

    def get_relationship(self, npc_a: str, npc_b: str) -> int:
        """获取两个NPC间的关系值（默认为0）"""
        return self._relationships.get(npc_a, {}).get(npc_b, 0)
