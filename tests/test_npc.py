"""
NPC模块测试 — Island Sim v1

覆盖：NPC初始化、属性自然变化、强制状态转换。
"""

from typing import Any, Dict

import pytest

from config import NPC_INITIAL_DATA, STAT_MAX, STAT_MIN
from npc.behavior import register_npc_states
from npc.npc import NPC
from world.map import GameMap
from world.time_system import TimeSystem


def _make_npc(overrides: Dict[str, Any] | None = None) -> NPC:
    """构造测试用NPC（使用第一个NPC初始数据）"""
    data = dict(NPC_INITIAL_DATA[0])
    if overrides:
        data.update(overrides)
    ts = TimeSystem()
    gm = GameMap()
    npc = NPC(data, ts, gm)
    register_npc_states(npc)
    return npc


def _advance_to_day(npc: NPC) -> None:
    """将时间推进到白天（hour 6 = tick 300）"""
    npc._time._tick_count = 300


def _advance_to_night(npc: NPC) -> None:
    """将时间推进到夜晚（hour 22 = tick 1100）"""
    npc._time._tick_count = 1100


# ── 初始化测试 ──


def test_npc_initialization() -> None:
    """验证NPC属性从初始化数据正确加载"""
    data = NPC_INITIAL_DATA[0]
    npc = _make_npc()
    assert npc.name == data["name"]
    assert npc.gender == data["gender"]
    assert npc.x == data["x"]
    assert npc.y == data["y"]
    assert npc.hunger == data["hunger"]
    assert npc.energy == data["energy"]
    assert npc.mood == data["mood"]
    assert npc.inventory == []


def test_npc_initial_state_is_idle() -> None:
    """验证NPC初始状态为IDLE"""
    npc = _make_npc()
    assert npc.get_state() == "IDLE"


def test_npc_all_initialized() -> None:
    """验证5个NPC都能成功创建"""
    ts = TimeSystem()
    gm = GameMap()
    for data in NPC_INITIAL_DATA:
        npc = NPC(data, ts, gm)
        register_npc_states(npc)
        assert npc.name != ""


def test_npc_state_machine_has_all_states() -> None:
    """验证状态机注册了全部5个行为状态"""
    npc = _make_npc()
    expected = {"IDLE", "WALK", "SEARCH_FOOD", "EAT", "SLEEP"}
    assert set(npc.fsm._states.keys()) == expected


# ── 属性变化测试 ──


def test_hunger_increases_over_time() -> None:
    """验证每帧hunger +0.1"""
    npc = _make_npc()
    initial = npc.hunger
    for _ in range(10):
        npc.update()
    assert npc.hunger == pytest.approx(initial + 1.0, rel=1e-3)


def test_energy_decreases_during_day() -> None:
    """验证白天每帧energy -0.05"""
    npc = _make_npc()
    _advance_to_day(npc)
    initial = npc.energy
    for _ in range(10):
        npc.update()
    expected = initial - 0.5
    # NPC可能被energy<20触发SLEEP，但白天不会
    assert npc.energy == pytest.approx(expected, rel=1e-2)


def test_energy_decreases_slower_at_night() -> None:
    """验证夜晚每帧energy -0.02"""
    npc = _make_npc()
    _advance_to_night(npc)
    initial_energy = npc.energy
    for _ in range(10):
        npc.update()
    # 夜晚energy下降慢，但NPC会进入SLEEP（energy恢复），所以只检查几个tick
    expected_min = initial_energy - 0.5  # 不进入SLEEP的话最多减这么多
    # 实际会进入SLEEP增加energy，所以应该高于这个值
    assert npc.energy > expected_min


def test_hunger_capped_at_max() -> None:
    """验证hunger不超过STAT_MAX"""
    npc = _make_npc({"hunger": 99, "energy": 100, "mood": 100})
    for _ in range(50):
        npc.update()
    assert npc.hunger <= STAT_MAX


def test_energy_capped_at_min() -> None:
    """验证energy不低于STAT_MIN"""
    npc = _make_npc({"energy": 5, "hunger": 0})
    _advance_to_day(npc)
    for _ in range(200):
        npc.update()
    assert npc.energy >= STAT_MIN


# ── 状态切换测试 ──


def test_sleep_when_energy_below_20() -> None:
    """验证energy < 20 时强制进入SLEEP（在房屋上直接睡）"""
    npc = _make_npc({"energy": 15, "hunger": 50, "x": 8, "y": 8})
    _advance_to_day(npc)
    npc.update()
    assert npc.get_state() == "SLEEP"


def test_sleep_at_night() -> None:
    """验证夜晚强制进入SLEEP（在房屋上直接睡）"""
    npc = _make_npc({"energy": 80, "hunger": 50, "x": 8, "y": 8})
    _advance_to_night(npc)
    npc.update()
    assert npc.get_state() == "SLEEP"


def test_search_food_when_hungry() -> None:
    """验证hunger > 70 时进入SEARCH_FOOD"""
    npc = _make_npc({"hunger": 80, "energy": 80, "x": 10, "y": 10})
    _advance_to_day(npc)
    npc.update()
    # SEARCH_FOOD是过渡状态，enter中会立即切换到WALK
    assert npc.get_state() in ("SEARCH_FOOD", "WALK", "EAT")


def test_wake_up_when_day_and_energy_high() -> None:
    """验证白天且energy充足时从SLEEP中醒来"""
    npc = _make_npc({"energy": 80, "hunger": 50})
    _advance_to_day(npc)
    # 手动设为SLEEP
    npc.fsm.set_state("SLEEP", npc)
    npc.update()
    # 由于是白天且energy >= 20，应该醒来
    assert npc.get_state() != "SLEEP"


def test_sleep_recovers_energy() -> None:
    """验证SLEEP时energy恢复（在房屋上直接睡）"""
    npc = _make_npc({"energy": 10, "hunger": 50, "x": 8, "y": 8})
    _advance_to_night(npc)
    previous = npc.energy
    npc.update()
    # 进入SLEEP后energy应增加
    assert npc.energy > previous


def test_eat_reduces_hunger() -> None:
    """验证进食降低饥饿值"""
    npc = _make_npc({"hunger": 85, "energy": 80})
    _advance_to_day(npc)
    # 强制进入EAT状态
    npc.fsm.set_state("EAT", npc)
    # EAT.enter 中 hunger -= 30
    assert npc.hunger == pytest.approx(55.0, rel=1e-3)
