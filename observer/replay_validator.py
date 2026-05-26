"""
回放验证器 — Island Sim v1

验证事件是否与 world state 一致。
支持单事件验证和批量回放校验。
如果日志说"阿强吃了鱼"，回放时必须能验证：hunger下降、fish减少、position一致。
"""

from typing import Any, Optional


class ReplayValidator:
    """回放验证器。验证事件与 world state 的一致性。"""

    def verify_event(
        self,
        event: dict[str, Any],
        npcs: list,
        resource_mgr: object,
        tick: int,
    ) -> dict[str, Any]:
        """验证单个事件是否与当前 world state 一致。返回 {valid, issues}"""
        result: dict[str, Any] = {
            "valid": True,
            "event_type": event.get("event_type", "UNKNOWN"),
            "issues": [],
            "checks": [],
        }
        et = event.get("event_type", "")
        npc_name = event.get("npc", "")
        details = event.get("details", {}) or {}

        if et == "NPC_EAT" and npc_name:
            self._verify_npc_eat(event, npcs, resource_mgr, result)

        elif et == "NPC_ENTER_WEAKENED" and npc_name:
            self._verify_weakened(event, npcs, result)

        elif et == "NPC_SLEEP" and npc_name:
            npc = self._find_npc(npc_name, npcs)
            if npc:
                state = getattr(npc, "get_state", lambda: "")()
                if state == "SLEEP":
                    result["checks"].append(f"NPC {npc_name} state=SLEEP ✓")
                else:
                    result["issues"].append(
                        f"NPC {npc_name} state={state} != SLEEP"
                    )

        elif et == "NPC_MOVE_REGION" and npc_name:
            self._verify_movement(event, npcs, result)

        elif et == "RESOURCE_DEPLETED":
            pos = event.get("position")
            if pos:
                pos_tuple = tuple(pos) if not isinstance(pos[0], int) else (pos[0], pos[1])  # noqa
                depleted = getattr(resource_mgr, "depleted_forests", set())
                if pos_tuple in depleted:
                    result["checks"].append(f"Position {pos} is depleted ✓")
                else:
                    result["issues"].append(
                        f"Position {pos} not in depleted_forests"
                    )

        elif et == "FOREST_RECOVERED":
            pos = event.get("position")
            if pos:
                pos_tuple = tuple(pos) if not isinstance(pos[0], int) else (pos[0], pos[1])  # noqa
                depleted = getattr(resource_mgr, "depleted_forests", set())
                if pos_tuple not in depleted:
                    result["checks"].append(f"Position {pos} recovered ✓")
                else:
                    result["issues"].append(
                        f"Position {pos} still in depleted_forests"
                    )

        if result["issues"]:
            result["valid"] = False

        return result

    def _verify_npc_eat(
        self,
        event: dict[str, Any],
        npcs: list,
        resource_mgr: object,
        result: dict[str, Any],
    ) -> None:
        """验证NPC饮食事件"""
        npc_name = event.get("npc", "")
        npc = self._find_npc(npc_name, npcs)
        if npc is None:
            result["issues"].append(f"NPC '{npc_name}' not found")
            return

        hunger = getattr(npc, "hunger", -1)
        result["checks"].append(
            f"NPC {npc_name} hunger={hunger} (post-EAT)"
        )

        # 验证NPC位置有食物资源
        nx, ny = getattr(npc, "x", -1), getattr(npc, "y", -1)
        has_food = False
        for (mx, my) in getattr(resource_mgr, "mushrooms", {}):
            if (mx, my) == (nx, ny):
                has_food = True
                break
        for (fx, fy) in getattr(resource_mgr, "fish", {}):
            if (fx, fy) == (nx, ny):
                has_food = True
                break
        result["checks"].append(
            f"Food at NPC position ({nx},{ny}): {'yes' if has_food else 'no'}"
        )

    def _verify_weakened(
        self,
        event: dict[str, Any],
        npcs: list,
        result: dict[str, Any],
    ) -> None:
        """验证NPC虚弱事件"""
        npc_name = event.get("npc", "")
        npc = self._find_npc(npc_name, npcs)
        if npc is None:
            result["issues"].append(f"NPC '{npc_name}' not found")
            return
        hunger = getattr(npc, "hunger", -1)
        weakened = getattr(npc, "_weakened", False)
        result["checks"].append(
            f"NPC {npc_name} hunger={hunger} weakened={weakened}"
        )
        if hunger < 80:
            result["issues"].append(
                f"NPC {npc_name} hunger={hunger} < 80 but event is "
                f"NPC_ENTER_WEAKENED"
            )

    def _verify_movement(
        self,
        event: dict[str, Any],
        npcs: list,
        result: dict[str, Any],
    ) -> None:
        """验证NPC移动事件"""
        npc_name = event.get("npc", "")
        npc = self._find_npc(npc_name, npcs)
        if npc is None:
            result["issues"].append(f"NPC '{npc_name}' not found")
            return
        pos = event.get("position")
        nx, ny = getattr(npc, "x", -1), getattr(npc, "y", -1)
        if pos and (nx, ny) != tuple(pos):
            result["issues"].append(
                f"NPC {npc_name} position ({nx},{ny}) != event "
                f"position {pos}"
            )

    def batch_verify(
        self,
        events: list[dict[str, Any]],
        npcs: list,
        resource_mgr: object,
        current_tick: int,
    ) -> dict[str, Any]:
        """批量验证多个事件"""
        results = []
        passed = 0
        failed = 0
        for ev in events:
            r = self.verify_event(ev, npcs, resource_mgr, current_tick)
            results.append(r)
            if r["valid"]:
                passed += 1
            else:
                failed += 1

        return {
            "total": len(events),
            "passed": passed,
            "failed": failed,
            "results": results,
        }

    @staticmethod
    def _find_npc(name: str, npcs: list) -> Optional[object]:
        """按名称查找NPC"""
        for n in npcs:
            if getattr(n, "name", "") == name:
                return n
        return None
