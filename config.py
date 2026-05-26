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
OVERLAY_HEATMAP: int = 4

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

# ── T-E003 热力图颜色 ──

HEATMAP_ALPHA: int = 100
"""热力叠加层透明度"""
HEATMAP_COLORS: list[tuple[int, int, int]] = [
    (40, 180, 40),    # 0.0 绿 — 低压/健康
    (120, 200, 40),   # 0.2 黄绿
    (200, 200, 40),   # 0.4 黄
    (220, 140, 40),   # 0.6 橙
    (200, 80, 40),    # 0.8 红橙
    (180, 40, 40),    # 1.0 红 — 高压/崩溃
]


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


# ── T-019 区域压力系统 ──

REGION_SIZE: int = 5
"""每个区域包含的tile数（20/5=4x4区域）"""


# ── T-020 NPC行为倾向 ──

NPC_BEHAVIOR_TRAITS: dict[str, dict[str, float]] = {
    "阿强": {"risk_tolerance": 0.8, "laziness": 0.3, "food_preference": 0.6, "exploration_bias": 0.7},
    "阿珍": {"risk_tolerance": 0.5, "laziness": 0.4, "food_preference": 0.5, "exploration_bias": 0.4},
    "大壮": {"risk_tolerance": 0.6, "laziness": 0.5, "food_preference": 0.4, "exploration_bias": 0.5},
    "小美": {"risk_tolerance": 0.3, "laziness": 0.4, "food_preference": 0.7, "exploration_bias": 0.3},
    "老李": {"risk_tolerance": 0.2, "laziness": 0.8, "food_preference": 0.3, "exploration_bias": 0.2},
}
"""每个NPC的行为倾向参数"""


# ── T-023 头模模拟 ──

HEADLESS_TICK_RATE: int = 1000
"""headless模式下每秒模拟tick数"""


# ── T-028 AI决策层 ──

AI_CONFIG: dict[str, object] = {
    "api_key": "sk-d7ecb163e0e14edb84ffc74297d5214c",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    # 每NPC每60秒最多1次API调用
    "rate_limit_seconds": 60,
    # API请求超时秒数
    "timeout": 10,
    # 每次响应的最大token数
    "max_tokens": 100,
    # 线程池最大并发数
    "max_workers": 2,
}
"""AI决策层的DeepSeek API配置"""


# ── T-027 地理生态层 ──

# 季节系统
SEASON_CYCLE_DAYS: int = 120
"""完整四季循环天数（每季30天）"""
SPRING_DAYS: int = 30
SUMMER_DAYS: int = 30
AUTUMN_DAYS: int = 30
WINTER_DAYS: int = 30

# 季节影响倍率
SEASON_MUSHROOM_BONUS: dict[str, float] = {
    "spring": 2.5, "summer": 1.0, "autumn": 1.5, "winter": 0.3,
}
"""蘑菇生成倍率：春季暴涨，冬季极少"""
SEASON_FISH_BONUS: dict[str, float] = {
    "spring": 1.0, "summer": 2.0, "autumn": 1.2, "winter": 0.2,
}
"""鱼类生成倍率：夏季丰产，冬季极少"""
SEASON_REGROWTH_BONUS: dict[str, float] = {
    "spring": 1.8, "summer": 1.2, "autumn": 0.8, "winter": 0.3,
}
"""森林恢复倍率：春季最快，冬季极慢"""
SEASON_ENERGY_COST: dict[str, float] = {
    "spring": 0.05, "summer": 0.06, "autumn": 0.08, "winter": 0.15,
}
"""每tick能量消耗：冬季最高"""
SEASON_HUNGER_RATE: dict[str, float] = {
    "spring": 0.1, "summer": 0.12, "autumn": 0.14, "winter": 0.18,
}
"""饥饿速度：冬季更快"""

# 地力系统
FERTILITY_TRAFFIC_DECAY: float = 0.00002
"""每单位人流量导致的 fertility 衰减 — FR-001a: 0.0001→0.00002"""
FERTILITY_RECOVERY_RATE: float = 0.005
"""每tick fertility 恢复速度（无人访问时）— FR-001a: 0.0005→0.005"""
FERTILITY_COLLAPSE_PENALTY: float = 0.03
"""一次 collapse 导致的 fertility 损失（分摊到每天）— FR-001a: 0.15→0.03"""
FERTILITY_BASE_REGEN: float = 0.002
"""fertility 向 base_fertility 回归速率 — FR-001a: 0.0001→0.002"""
FERTILITY_MIN: float = 0.05
"""fertility 下限"""
FERTILITY_MAX: float = 1.0
"""fertility 上限"""
FERTILITY_SPAWN_MULT_MIN: float = 0.5
"""fertility 最低资源生成倍率（fert=0.0时）"""
FERTILITY_SPAWN_MULT_MAX: float = 1.5
"""fertility 最高资源生成倍率（fert=1.0时）"""

# 空间生态（压力扩散）
SPATIAL_DIFFUSION_RATE: float = 0.02
"""每tick压力向邻居扩散量"""
SPATIAL_RECOVERY_SPREAD: float = 0.01
"""低压力区对邻居的恢复扩散量"""
SPATIAL_DIFFUSION_MIN: float = 0.1
"""触发扩散的最小压力值"""
SPATIAL_RECOVERY_BONUS_MAX: float = 0.15
"""邻居给予的最大恢复加成"""

# 生态避难所（Refugia）天然高 fertility 区域
REFUGIA_THRESHOLD: float = 0.65
"""fertility >= 此值视为潜在避难所"""
REFUGIA_COLLAPSE_RESISTANCE: float = 0.15
"""避难所区域 collapse 阈值额外提升"""
REFUGIA_RECOVERY_BONUS: float = 1.5
"""避难所恢复速度倍率"""

# 迁徙走廊
MIGRATION_CORRIDOR_THRESHOLD: int = 10
"""达到此阈值认定一条迁徙走廊形成"""
MIGRATION_TRACK_WINDOW: int = 3600
"""迁徙统计的tick窗口"""

# 地理报告间隔
GEO_REPORT_INTERVAL: int = 2400
"""每2400 tick 输出一次地理报告（约2天）"""
