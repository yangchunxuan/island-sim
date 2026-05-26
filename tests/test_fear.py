"""
FR-002 NPC恐惧系统测试 — Island Sim v1

覆盖：fear属性变化、范围约束、行为影响。
"""

from typing import Any, Dict

import pytest

from config import (
    FEAR_DECAY_RATE,
    FEAR_FLEE_THRESHOLD,
    FEAR_HUNGER_THRESHOLD,
    FEAR_INCREASE_RATE,
    FEAR_MAX,
    NPC_INITIAL_DATA,
    STAT_MAX,
    TileType,
)
from npc.behavior import register_npc_states
from npc.npc import NPC
from world.map import GameMap
from world.resources import ResourceManager
from world.time_system import TimeSystem


def _make_npc(overrides: Dict[str, Any] | None = None,
              with_resources: bool = True) -> NPC:
    """构造测试用NPC（使用第一个NPC初始数据）"""
    data = dict(NPC_INITIAL_DATA[0])
    if overrides:
        data.update(overrides)
    ts = TimeSystem()
    gm = GameMap()
    rm = ResourceManager(gm._grid) if with_resources else None
    npc = NPC(data, ts, gm, resource_mgr=rm)
    register_npc_states(npc)
    return npc


def _advance_to_day(npc: NPC) -> None:
    """将时间推进到白天（hour 6 = tick 300）"""
    npc._time._tick_count = 300


# ── fear 基础属性测试 ──


def test_fear_increases_when_hungry() -> None:
    """验证 hunger > FEAR_HUNGER_THRESHOLD 时 fear 每 tick 增加"""
    npc = _make_npc({"hunger": FEAR_HUNGER_THRESHOLD + 1, "energy": 100})
    _advance_to_day(npc)
    assert npc.fear == 0.0

    ticks = 10
    for _ in range(ticks):
        npc.update()

    expected = ticks * FEAR_INCREASE_RATE
    assert npc.fear == pytest.approx(expected, rel=1e-3)


def test_fear_decays_when_fed() -> None:
    """验证 hunger < FEAR_HUNGER_THRESHOLD 时 fear 每 tick 衰减"""
    npc = _make_npc({"hunger": 30, "energy": 100})
    _advance_to_day(npc)
    npc.fear = 0.8

    ticks = 10
    for _ in range(ticks):
        npc.update()

    expected = 0.8 - ticks * FEAR_DECAY_RATE
    assert npc.fear == pytest.approx(expected, rel=1e-3)


# ── clamp 测试 ──


def test_fear_clamped_to_zero() -> None:
    """验证 fear 不低于 0"""
    npc = _make_npc({"hunger": 0, "energy": 100})
    _advance_to_day(npc)
    npc.fear = 0.1

    for _ in range(20):
        npc.update()

    assert npc.fear == 0.0


def test_fear_clamped_to_max() -> None:
    """验证 fear 不超过 FEAR_MAX"""
    npc = _make_npc({"hunger": 90, "energy": 100})
    _advance_to_day(npc)
    npc.fear = FEAR_MAX - 0.1

    for _ in range(50):
        npc.update()

    assert npc.fear == pytest.approx(FEAR_MAX, rel=1e-3)


# ── 行为影响测试 ──


def test_high_fear_affects_behavior() -> None:
    """验证 fear > FEAR_FLEE_THRESHOLD 时觅食回避近距离食物"""
    # 高恐惧 NPC
    npc_fearful = _make_npc({"name": "阿强", "hunger": 60, "energy": 100,
                              "risk_tolerance": 0.9},
                             with_resources=True)
    _advance_to_day(npc_fearful)
    npc_fearful.fear = FEAR_FLEE_THRESHOLD + 0.1  # > 0.7

    # 冷静 NPC（对照）
    npc_calm = _make_npc({"name": "阿珍", "hunger": 60, "energy": 100,
                           "risk_tolerance": 0.9},
                          with_resources=True)
    _advance_to_day(npc_calm)
    npc_calm.fear = 0.0

    # 放在同一位置
    npc_fearful.x = npc_fearful.y = 5
    npc_calm.x = npc_calm.y = 5

    # 触发觅食
    npc_fearful.fsm.set_state("SEARCH_FOOD", npc_fearful)
    npc_calm.fsm.set_state("SEARCH_FOOD", npc_calm)

    # 无可用食物时两者都应找不到
    if npc_calm.target_x is None:
        assert npc_fearful.target_x is None
        return

    assert npc_fearful.target_x is not None

    # 高恐惧 NPC 选择的食物距离应 >= 冷静 NPC 的选择
    dist_fearful = abs(npc_fearful.target_x - 5) + abs(npc_fearful.target_y - 5)
    dist_calm = abs(npc_calm.target_x - 5) + abs(npc_calm.target_y - 5)

    assert dist_fearful >= dist_calm, \
        f"高恐惧应回避近处食物: fearful_dist={dist_fearful}, calm_dist={dist_calm}"
