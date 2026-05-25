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


# ── NPC初始数据 ──

NPC_INITIAL_DATA: List[Dict[str, Any]] = [
    {"name": "阿强", "gender": "male",   "x": 3,  "y": 3,  "hunger": 50, "energy": 80, "mood": 60, "inventory": [], "state": "IDLE"},
    {"name": "阿珍", "gender": "female", "x": 7,  "y": 4,  "hunger": 40, "energy": 90, "mood": 70, "inventory": [], "state": "IDLE"},
    {"name": "大壮", "gender": "male",   "x": 12, "y": 5,  "hunger": 60, "energy": 70, "mood": 50, "inventory": [], "state": "IDLE"},
    {"name": "小美", "gender": "female", "x": 5,  "y": 12, "hunger": 30, "energy": 85, "mood": 80, "inventory": [], "state": "IDLE"},
    {"name": "老李", "gender": "male",   "x": 14, "y": 14, "hunger": 70, "energy": 60, "mood": 40, "inventory": [], "state": "IDLE"},
]
"""5个固定NPC的初始属性"""


# ── 属性范围 ──

STAT_MIN: int = 0
STAT_MAX: int = 100
"""NPC基本属性（hunger/energy/mood）的取值范围"""


# ── 时间系统 ──

DAY_TICKS: int = 1200
"""一个完整的白天+夜晚所需的tick数（60FPS下约20秒）"""
