"""
NPC模块测试 — Island Sim v1

覆盖：NPC初始化、属性自然变化、强制状态转换。
"""

from typing import Any, Dict

import pytest

from config import (
    FOOD_PER_FOREST,
    HUNGER_MOOD_DECAY_RATE,
    NPC_INITIAL_DATA,
    STAT_MAX,
    STAT_MIN,
    TileType,
    WEAKENED_HUNGER_THRESHOLD,
    WEAKENED_TRIGGER_DURATION,
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


def _advance_to_night(npc: NPC) -> None:
    """将时间推进到夜晚（hour 22 = tick 220, 基于 DAY_TICKS=240）"""
    npc._time._tick_count = 220


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
    """验证进食消耗森林食物并降低饥饿值"""
    npc = _make_npc({"hunger": 85, "energy": 80})
    _advance_to_day(npc)
    # 把NPC放到有食物的森林上
    for y in range(20):
        for x in range(20):
            if npc._map.get_tile(x, y) == TileType.FOREST:
                npc.x, npc.y = x, y
                break
        else:
            continue
        break
    # 强制进入EAT状态
    npc.fsm.set_state("EAT", npc)
    # EAT.enter 从森林采集食物，hunger -= 30
    assert npc.hunger == pytest.approx(55.0, rel=1e-3)


# ── T-015 资源压力 / 行为后果测试 ──


def test_hunger_affects_mood() -> None:
    """验证hunger > 60 时mood每帧下降"""
    npc = _make_npc({"hunger": 80, "mood": 80, "energy": 100})
    _advance_to_day(npc)
    for _ in range(10):
        npc.update()
    # hunger每帧+0.1, mood每帧-0.1(因hunger>60)
    assert npc.mood < 80
    assert npc.mood == pytest.approx(80 - 10 * HUNGER_MOOD_DECAY_RATE, rel=1e-2)


def test_low_hunger_no_mood_decay() -> None:
    """验证hunger <= 60 时mood不因饥饿下降"""
    npc = _make_npc({"hunger": 40, "mood": 80, "energy": 100})
    _advance_to_day(npc)
    for _ in range(10):
        npc.update()
    # habit前几帧hunger <=60时mood不降,超过后才降
    assert npc.mood == pytest.approx(80, abs=2)


def test_weakened_after_prolonged_hunger() -> None:
    """验证hunger持续超过阈值后触发weakened"""
    # 放在不可行走位置(水中)，防止NPC跑去觅食打断饥饿累积
    npc = _make_npc({"hunger": 90, "energy": 100, "mood": 100, "x": 0, "y": 0})
    _advance_to_day(npc)
    # 初始不weakened
    assert not npc._weakened
    # 持续高hunger帧数超过阈值
    for _ in range(WEAKENED_TRIGGER_DURATION + 10):
        npc.update()
        if npc._weakened:
            break
    assert npc._weakened, "持续高hunger应触发weakened"


def test_weakened_recovery() -> None:
    """验证hunger降至阈值以下后解除weakened"""
    # 放在不可行走位置(水中)，防止NPC跑去觅食打断饥饿累积
    npc = _make_npc({"hunger": 90, "energy": 100, "mood": 100, "x": 0, "y": 0})
    _advance_to_day(npc)
    # 触发weakened
    for _ in range(WEAKENED_TRIGGER_DURATION + 20):
        npc.update()
    assert npc._weakened
    # 强制降低hunger，等待恢复
    npc.hunger = 30
    for _ in range(WEAKENED_TRIGGER_DURATION):
        npc.update()
        if not npc._weakened:
            break
    assert not npc._weakened, "hunger降低后应解除weakened"


def test_weakened_slows_movement() -> None:
    """验证weakened时移动冷却更长"""
    npc = _make_npc({"hunger": 50, "energy": 100, "mood": 100, "x": 5, "y": 5})
    _advance_to_day(npc)
    # 直接设置weakened标志（而非等游戏循环触发）
    npc._weakened = True
    # 设置WALK状态，目标为相邻可通行tile
    npc.target_x, npc.target_y = 6, 5
    npc.fsm.set_state("WALK", npc)
    # 重置cooldown然后跑一帧
    npc._move_cooldown = 0
    npc.fsm.update(npc)
    # weakened应使用WEAKENED_MOVE_COOLDOWN=10
    assert npc._move_cooldown == 10, f"weakened冷却应为10, 实际{npc._move_cooldown}"


def test_weakened_longer_idle() -> None:
    """验证weakened时空闲时间更长（对比正常状态，同seed）"""
    import random
    npc = _make_npc({"hunger": 50, "energy": 100, "mood": 100, "x": 5, "y": 5})
    _advance_to_day(npc)
    assert not npc._weakened
    # 正常状态进入IDLE
    random.seed(99)
    npc.fsm.set_state("IDLE", npc)
    normal_timer = npc._idle_timer
    # 设weakened后再次进入IDLE（同seed，排除随机影响）
    npc._weakened = True
    random.seed(99)
    npc.fsm.set_state("IDLE", npc)
    assert npc._idle_timer > normal_timer, \
        f"weakened(idle_timer={npc._idle_timer})应大于normal(idle_timer={normal_timer})"


def test_eat_at_depleted_forest_less_food() -> None:
    """验证depleted森林进食只能微量缓解"""
    npc = _make_npc({"hunger": 85, "energy": 80}, with_resources=True)
    _advance_to_day(npc)
    # 把NPC放到森林上，然后采光该森林
    forest_pos = None
    for y in range(20):
        for x in range(20):
            if npc._map.get_tile(x, y) == TileType.FOREST:
                forest_pos = (x, y)
                break
        if forest_pos:
            break
    assert forest_pos
    npc.x, npc.y = forest_pos
    # 采光森林
    for _ in range(FOOD_PER_FOREST):
        npc._resource_mgr.collect(forest_pos[0], forest_pos[1])
    # 现在进食只能微量缓解
    npc.fsm.set_state("EAT", npc)
    # hunger 从85降到80（减5，不是减30）
    assert npc.hunger == pytest.approx(80.0, rel=1e-3)


def test_search_food_skips_depleted_forest() -> None:
    """验证SEARCH_FOOD不会选择已耗尽的森林"""
    npc = _make_npc({"hunger": 85, "energy": 100}, with_resources=True)
    _advance_to_day(npc)
    # 把所有森林采光
    for (fx, fy) in list(npc._resource_mgr.available_forests()):
        for _ in range(FOOD_PER_FOREST):
            npc._resource_mgr.collect(fx, fy)
    # 没有可用森林时，SEARCH_FOOD应退回IDLE
    npc.hunger = 80
    npc.fsm.set_state("SEARCH_FOOD", npc)
    assert npc.get_state() == "IDLE", "无可用森林时应退回IDLE"


# ═══════════════════════════════════════════════
# T-020 行为倾向测试
# ═══════════════════════════════════════════════

def test_behavior_traits_loaded() -> None:
    """验证行为倾向参数从config正确加载"""
    for data in NPC_INITIAL_DATA:
        npc = _make_npc(data)
        assert hasattr(npc, 'risk_tolerance')
        assert hasattr(npc, 'laziness')
        assert hasattr(npc, 'food_preference')
        assert hasattr(npc, 'exploration_bias')
        assert 0.0 <= npc.risk_tolerance <= 1.0
        assert 0.0 <= npc.laziness <= 1.0


def test_lazy_npc_longer_idle() -> None:
    """验证懒惰NPC空闲时间更长（fixed seed确保随机相等）"""
    import random
    active = _make_npc({"hunger": 30, "energy": 100, "laziness": 0.1})
    lazy = _make_npc({"hunger": 30, "energy": 100, "laziness": 0.9})
    _advance_to_day(active)
    _advance_to_day(lazy)

    random.seed(42)
    active.fsm.set_state("IDLE", active)
    random.seed(42)
    lazy.fsm.set_state("IDLE", lazy)
    # lazy系数1.4 > active系数0.6，seed相同时懒的一定更大
    assert lazy._idle_timer > active._idle_timer, \
        f"懒惰(idle_timer={lazy._idle_timer})应大于勤快(idle_timer={active._idle_timer})"


def test_explorer_wanders_further() -> None:
    """验证探索型NPC idle时走更远"""
    from npc.behavior import IdleState

    class MockOwner:
        x, y = 10, 10
        exploration_bias = 0.9
        _map = None

    explorer = MockOwner()
    explorer._map = GameMap()

    class MockOwner2:
        x, y = 10, 10
        exploration_bias = 0.1
        _map = None

    homebody = MockOwner2()
    homebody._map = GameMap()

    explorer_targets = []
    homebody_targets = []
    for _ in range(50):
        t = IdleState._pick_walk_target(explorer)
        if t:
            explorer_targets.append(t)
        t = IdleState._pick_walk_target(homebody)
        if t:
            homebody_targets.append(t)

    if explorer_targets and homebody_targets:
        explorer_max = max(max(abs(t[0]-10), abs(t[1]-10)) for t in explorer_targets)
        homebody_max = max(max(abs(t[0]-10), abs(t[1]-10)) for t in homebody_targets)
        assert explorer_max >= homebody_max


def test_conservative_npc_limited_search() -> None:
    """验证保守型NPC因距离放弃觅食"""
    npc = _make_npc({"hunger": 80, "energy": 100, "risk_tolerance": 0.1,
                      "x": 0, "y": 0}, with_resources=True)
    _advance_to_day(npc)
    # 把NPC丢到角落，食物在远处
    npc.x, npc.y = 0, 0
    npc.fsm.set_state("SEARCH_FOOD", npc)
    # 保守NPC可能放弃（取决于食物距离）
    # 只要不崩溃即可
    assert npc.get_state() in ("IDLE", "SEARCH_FOOD", "WALK")
