"""
World Seed 架构测试 — Island Sim v1

验证 world_seed/ 目录下的世界宪法文件：
- YAML 可正确读取
- region 唯一
- ecology rules 完整
- traits 合法
- observer style 字段完整
- history.md 非空
"""

import os
import unittest

import yaml

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
SEED_DIR = os.path.join(BASE_DIR, "world_seed")


class TestWorldSeedFilesExist(unittest.TestCase):
    """验证 world_seed/ 下所有必需文件存在"""

    def test_history_md_exists(self):
        self.assertTrue(os.path.exists(os.path.join(SEED_DIR, "history.md")))

    def test_ecology_rules_yaml_exists(self):
        self.assertTrue(os.path.exists(os.path.join(SEED_DIR, "ecology_rules.yaml")))

    def test_regions_yaml_exists(self):
        self.assertTrue(os.path.exists(os.path.join(SEED_DIR, "regions.yaml")))

    def test_npc_traits_yaml_exists(self):
        self.assertTrue(os.path.exists(os.path.join(SEED_DIR, "npc_traits.yaml")))

    def test_observer_style_yaml_exists(self):
        self.assertTrue(os.path.exists(os.path.join(SEED_DIR, "observer_style.yaml")))

    def test_world_constants_yaml_exists(self):
        self.assertTrue(os.path.exists(os.path.join(
            SEED_DIR, "world_constants.yaml",
        )))


class TestHistoryMd(unittest.TestCase):
    """验证 history.md"""

    def test_length_between_50_and_150_lines(self):
        path = os.path.join(SEED_DIR, "history.md")
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertGreaterEqual(len(lines), 50)
        self.assertLessEqual(len(lines), 150)

    def test_not_empty(self):
        path = os.path.join(SEED_DIR, "history.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        self.assertTrue(len(content) > 0)

    def test_no_destiny_or_prophecy_keywords(self):
        path = os.path.join(SEED_DIR, "history.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().lower()
        forbidden = ["救世主", "命运", "预言", "主线任务", "chosen"]
        for kw in forbidden:
            self.assertNotIn(kw, content,
                             f"history.md must not contain '{kw}'")


class TestEcologyRulesYaml(unittest.TestCase):
    """验证 ecology_rules.yaml 完整性"""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(SEED_DIR, "ecology_rules.yaml")
        with open(path, "r", encoding="utf-8") as f:
            cls.data = yaml.safe_load(f)

    def test_has_required_sections(self):
        """必须包含6个必拆分子节"""
        required = [
            "resource_cycle",
            "ecosystem_pressure",
            "migration_rules",
            "recovery_rules",
            "climate_rules",
            "decay_rules",
        ]
        for section in required:
            self.assertIn(section, self.data,
                          f"ecology_rules must contain '{section}'")

    def test_resource_cycle_has_forest(self):
        self.assertIn("forest", self.data["resource_cycle"])

    def test_ecosystem_pressure_has_thresholds(self):
        self.assertIn("thresholds", self.data["ecosystem_pressure"])

    def test_climate_rules_has_rain(self):
        self.assertIn("rain", self.data["climate_rules"])


class TestRegionsYaml(unittest.TestCase):
    """验证 regions.yaml 区域数据"""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(SEED_DIR, "regions.yaml")
        with open(path, "r", encoding="utf-8") as f:
            cls.data = yaml.safe_load(f)
        cls.regions = cls.data.get("regions", [])

    def test_at_least_4_regions(self):
        self.assertGreaterEqual(len(self.regions), 4)

    def test_region_ids_unique(self):
        ids = [r["id"] for r in self.regions]
        self.assertEqual(len(ids), len(set(ids)),
                         "Region IDs must be unique")

    def test_no_duplicate_grid_positions(self):
        """每个 grid_x, grid_y 组合唯一"""
        positions = [(r["grid_x"], r["grid_y"]) for r in self.regions]
        self.assertEqual(len(positions), len(set(positions)),
                         "Each grid position must be unique")

    def test_each_region_has_required_fields(self):
        """每个区域必须包含 resource_bias, danger_level, fertility, humidity, traffic_score"""
        for r in self.regions:
            with self.subTest(region=r["id"]):
                self.assertIn("resource_bias", r)
                self.assertIn("danger_level", r)
                self.assertIn("fertility", r)
                self.assertIn("humidity", r)
                self.assertIn("traffic_score", r)

    def test_resource_bias_has_valid_values(self):
        """resource_bias 值必须在 0.0~1.0 范围"""
        for r in self.regions:
            for k, v in r.get("resource_bias", {}).items():
                with self.subTest(region=r["id"], bias=k):
                    self.assertGreaterEqual(v, 0.0)
                    self.assertLessEqual(v, 1.0)


class TestNpcTraitsYaml(unittest.TestCase):
    """验证 npc_traits.yaml"""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(SEED_DIR, "npc_traits.yaml")
        with open(path, "r", encoding="utf-8") as f:
            cls.data = yaml.safe_load(f)

    def test_has_npcs_list(self):
        self.assertIn("npcs", self.data)

    def test_npc_ids_unique(self):
        ids = [n["id"] for n in self.data["npcs"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_each_npc_has_name(self):
        for n in self.data["npcs"]:
            with self.subTest(npc=n["id"]):
                self.assertIn("name", n)

    def test_no_personality_traits(self):
        """禁止使用人格特质关键词"""
        forbidden = ["善良", "邪恶", "开朗", "kind", "evil", "cheerful"]
        for n in self.data["npcs"]:
            for k in n.keys():
                for kw in forbidden:
                    self.assertNotIn(kw, str(k).lower())

    def test_trait_values_in_range(self):
        """所有数值型 trait 值必须在 0.0~1.0"""
        for n in self.data["npcs"]:
            for k, v in n.items():
                if isinstance(v, (int, float)) and k not in ("id", "name"):
                    with self.subTest(npc=n["id"], trait=k):
                        self.assertGreaterEqual(v, 0.0)
                        self.assertLessEqual(v, 1.0)


class TestObserverStyleYaml(unittest.TestCase):
    """验证 observer_style.yaml"""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(SEED_DIR, "observer_style.yaml")
        with open(path, "r", encoding="utf-8") as f:
            cls.data = yaml.safe_load(f)

    def test_has_style(self):
        self.assertIn("style", self.data)

    def test_has_tone(self):
        self.assertIn("tone", self.data)

    def test_has_detail_level(self):
        self.assertIn("detail_level", self.data)

    def test_has_levels(self):
        self.assertIn("levels", self.data)

    def test_levels_contain_INFO_WARNING_CRITICAL(self):
        for level in ("INFO", "WARNING", "CRITICAL"):
            self.assertIn(level, self.data.get("levels", {}))

    def test_has_format(self):
        self.assertIn("format", self.data)


class TestWorldConstantsYaml(unittest.TestCase):
    """验证 world_constants.yaml"""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(SEED_DIR, "world_constants.yaml")
        with open(path, "r", encoding="utf-8") as f:
            cls.data = yaml.safe_load(f)

    def test_has_world_cycles(self):
        self.assertIn("world_cycles", self.data)

    def test_has_log_limits(self):
        self.assertIn("log_limits", self.data)

    def test_log_limits_has_live_feed_max(self):
        self.assertIn("live_feed_max", self.data.get("log_limits", {}))

    def test_has_npc_parameters(self):
        self.assertIn("npc_parameters", self.data)


if __name__ == "__main__":
    unittest.main()
