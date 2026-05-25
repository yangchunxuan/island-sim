"""
全局配置文件 — Island Sim v1

所有游戏常量统一在此定义，禁止在其他模块中使用magic number。
"""

from enum import IntEnum
from typing import Any, Dict, List


# ── 地图基础 ──

TILE_SIZE: int = 32
"""每个tile的像素尺寸（正方形）"""

MAP_WIDTH: int = 20
"""地图横向tile数量"""

MAP_HEIGHT: int = 20
"""地图纵向tile数量"""


# ── 窗口 ──

SIDEBAR_WIDTH: int = 160
"""右侧状态栏宽度"""

WINDOW_WIDTH: int = MAP_WIDTH * TILE_SIZE + SIDEBAR_WIDTH  # 800
"""窗口总宽度（像素）"""

WINDOW_HEIGHT: int = MAP_HEIGHT * TILE_SIZE  # 640
"""窗口总高度（像素）"""

FPS: int = 60
"""游戏帧率"""


# ── Tile类型 ──

class TileType(IntEnum):
    """地图tile类型枚举"""
    WATER = 0
    SAND = 1
    GRASS = 2
    FOREST = 3
    ROCK = 4
    HOUSE = 5
    CAMPFIRE = 6


# ── 颜色定义（R, G, B） ──

COLOR_WATER: tuple[int, int, int] = (65, 105, 225)       # 海水蓝
COLOR_SAND: tuple[int, int, int] = (238, 214, 175)       # 沙滩黄
COLOR_GRASS: tuple[int, int, int] = (34, 139, 34)        # 草地绿
COLOR_FOREST: tuple[int, int, int] = (0, 100, 0)         # 深森林绿
COLOR_ROCK: tuple[int, int, int] = (128, 128, 128)       # 岩石灰
COLOR_HOUSE: tuple[int, int, int] = (139, 69, 19)        # 房屋棕
COLOR_CAMPFIRE: tuple[int, int, int] = (255, 140, 0)     # 篝火橙
COLOR_BLACK: tuple[int, int, int] = (0, 0, 0)
COLOR_WHITE: tuple[int, int, int] = (255, 255, 255)
COLOR_SIDEBAR_BG: tuple[int, int, int] = (30, 30, 30)    # 侧栏深灰背景

# tile类型 -> 颜色映射
TILE_COLORS: dict[TileType, tuple[int, int, int]] = {
    TileType.WATER: COLOR_WATER,
    TileType.SAND: COLOR_SAND,
    TileType.GRASS: COLOR_GRASS,
    TileType.FOREST: COLOR_FOREST,
    TileType.ROCK: COLOR_ROCK,
    TileType.HOUSE: COLOR_HOUSE,
    TileType.CAMPFIRE: COLOR_CAMPFIRE,
}

# ── Tile属性 ──

TILE_PROPERTIES: dict[TileType, dict[str, object]] = {
    TileType.WATER:   {"walkable": False, "resource_type": None, "can_sleep": False, "can_socialize": False},
    TileType.SAND:    {"walkable": True,  "resource_type": None, "can_sleep": False, "can_socialize": False},
    TileType.GRASS:   {"walkable": True,  "resource_type": None, "can_sleep": False, "can_socialize": False},
    TileType.FOREST:  {"walkable": True,  "resource_type": "food", "can_sleep": False, "can_socialize": False},
    TileType.ROCK:    {"walkable": False, "resource_type": None, "can_sleep": False, "can_socialize": False},
    TileType.HOUSE:   {"walkable": True,  "resource_type": None, "can_sleep": True,  "can_socialize": False},
    TileType.CAMPFIRE:{"walkable": True,  "resource_type": None, "can_sleep": False, "can_socialize": True},
}
"""每种tile类型的行为属性:
walkable — NPC能否通行;
resource_type — 可采集的资源类型 (None/\"food\");
can_sleep — NPC能否在此睡觉;
can_socialize — NPC能否在此社交。
	"""

# ── NPC状态颜色 ──

STATE_COLORS: dict[str, tuple[int, int, int]] = {
    "IDLE": (255, 255, 255),        # 白色
    "WALK": (0, 200, 0),            # 绿色
    "SEARCH_FOOD": (255, 255, 0),   # 黄色
    "EAT": (255, 165, 0),           # 橙色
    "SLEEP": (0, 100, 255),         # 蓝色
}

# NPC名称拼音（中文可能显示不了用拼音）
NPC_NAME_PINYIN: dict[str, str] = {
    "阿强": "A-Qiang",
    "阿珍": "A-Zhen",
    "大壮": "Da-Zhuang",
    "小美": "Xiao-Mei",
    "老李": "Lao-Li",
}


# ── NPC初始数据 ──

NPC_INITIAL_DATA: List[Dict[str, Any]] = [
    {"name": "阿强", "gender": "male",   "x": 5,  "y": 5,  "hunger": 50, "energy": 80, "mood": 60, "inventory": [], "state": "IDLE"},
    {"name": "阿珍", "gender": "female", "x": 7,  "y": 4,  "hunger": 40, "energy": 90, "mood": 70, "inventory": [], "state": "IDLE"},
    {"name": "大壮", "gender": "male",   "x": 12, "y": 5,  "hunger": 60, "energy": 70, "mood": 50, "inventory": [], "state": "IDLE"},
    {"name": "小美", "gender": "female", "x": 5,  "y": 12, "hunger": 30, "energy": 85, "mood": 80, "inventory": [], "state": "IDLE"},
    {"name": "老李", "gender": "male",   "x": 14, "y": 14, "hunger": 70, "energy": 60, "mood": 40, "inventory": [], "state": "IDLE"},
]
"""5个固定NPC的初始属性"""


# ── T-017 生态循环 ──

# 森林恢复
FOREST_REGROWTH_DAYS: int = 25
"""depleted森林自动恢复所需天数"""

# 蘑菇系统
MUSHROOM_SPAWN_CHANCE: float = 0.002
"""每帧每个候选tile的蘑菇生成概率"""
MUSHROOM_SPAWN_NIGHT_MULT: float = 2.5
"""夜晚生成概率倍率"""
MUSHROOM_FRESH_DURATION: int = 240
"""fresh阶段持续帧数（约4秒）"""
MUSHROOM_OLD_DURATION: int = 180
"""old阶段持续帧数（约3秒）"""
MUSHROOM_ROTTEN_DURATION: int = 120
"""rotten阶段持续帧数（约2秒），之后消失"""
MUSHROOM_NUTRITION_FRESH: int = 15
"""fresh蘑菇减少饥饿值"""
MUSHROOM_NUTRITION_OLD: int = 8
"""old蘑菇减少饥饿值"""

# 鱼类系统
FISH_SPAWN_CHANCE: float = 0.003
"""每帧每个候选tile的鱼生成概率"""
FISH_SPAWN_NIGHT_REDUCTION: float = 0.3
"""夜晚生成概率降低比例"""
FISH_LIFETIME: int = 300
"""鱼存在帧数（约5秒）"""
FISH_NUTRITION: int = 12
"""鱼减少的饥饿值"""

# 资源热点
HOTSPOT_MUSHROOM_MULT: float = 3.0
"""蘑菇热点区域生成概率倍率"""
HOTSPOT_FISH_MULT: float = 2.5
"""鱼类热点区域生成概率倍率"""

# 人流量追踪
TRAFFIC_DECAY: float = 0.998
"""每帧人流量衰减系数"""
TRAFFIC_REGROWTH_PENALTY: float = 0.5
"""高流量区域的恢复速度倍率（值越低恢复越慢）"""
TRAFFIC_HIGH_THRESHOLD: float = 50.0
"""判定为高流量的阈值"""


# ── 属性范围 ──

STAT_MIN: int = 0
STAT_MAX: int = 100
"""NPC基本属性（hunger/energy/mood）的取值范围"""


# ── 资源系统 ──

FOOD_PER_FOREST: int = 3
"""每个FOREST tile的初始食物储量，归零后永久depleted"""


# ── NPC Weakened 系统 ──

WEAKENED_HUNGER_THRESHOLD: int = 80
"""hunger超过此阈值持续一段时间后NPC进入weakened状态"""

WEAKENED_RECOVERY_THRESHOLD: int = 50
"""hunger低于此阈值并稳定后退出weakened状态"""

WEAKENED_TRIGGER_DURATION: int = 60
"""hunger超过阈值持续此帧数后触发weakened（约1秒）"""

WEAKENED_MOVE_COOLDOWN: int = 10
"""weakened状态下的移动冷却帧数（正常为5）"""

WEAKENED_IDLE_MULTIPLIER: float = 2.0
"""weakened状态下的空闲时间倍率"""

HUNGER_MOOD_DECAY_RATE: float = 0.1
"""hunger > 60 时mood每帧衰减量"""


# ── 时间系统 ──

DAY_TICKS: int = 1200
"""一个完整的白天+夜晚所需的tick数（60FPS下约20秒）"""


# ── Debug Overlay ──

OVERLAY_NONE: int = 0
OVERLAY_TILE: int = 1
OVERLAY_STATS: int = 2
OVERLAY_PATH: int = 3

# ── T-016 可视化常量 ──

COLOR_DEPLETED_FOREST: tuple[int, int, int] = (80, 95, 70)
"""depleted森林的灰绿色"""

NIGHT_OVERLAY_ALPHA: int = 80
"""夜晚遮罩alpha值（0-255）"""

COLOR_WEAKENED_RING: tuple[int, int, int] = (160, 160, 160)
"""weakened NPC灰色指示环"""

HUD_FOOD_COLOR: tuple[int, int, int] = (100, 200, 100)
HUD_DEPLETED_COLOR: tuple[int, int, int] = (200, 100, 100)
HUD_WEAKENED_COLOR: tuple[int, int, int] = (200, 200, 100)
HUD_MOOD_COLOR: tuple[int, int, int] = (100, 150, 255)


# Tile类型缩写（debug网格用）
TILE_LABELS: dict[TileType, str] = {
    TileType.WATER: "W",
    TileType.SAND: "S",
    TileType.GRASS: "G",
    TileType.FOREST: "F",
    TileType.ROCK: "R",
    TileType.HOUSE: "H",
    TileType.CAMPFIRE: "C",
}
