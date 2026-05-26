"""
迁徙走廊测试 — Island Sim v1 (T-027)

验证：区域间移动追踪、走廊形成检测、净流动计算。
"""

from config import MIGRATION_CORRIDOR_THRESHOLD
from observer.region_tracker import RegionTracker


class TestCorridorTracking:
    """迁徙走廊追踪测试"""

    def test_single_move_no_corridor(self):
        rt = RegionTracker()
        rt.record_visit(2, 2, "阿强", 100)
        rt.record_visit(7, 7, "阿强", 200)
        corridors = rt.get_migration_corridors()
        assert len(corridors) == 0

    def test_corridor_forms_at_threshold(self):
        rt = RegionTracker()
        for i in range(MIGRATION_CORRIDOR_THRESHOLD + 2):
            rt.record_visit(2, 2, f"NPC{i}", i * 10)
            rt.record_visit(7, 7, f"NPC{i}", i * 10 + 5)
        corridors = rt.get_migration_corridors()
        assert len(corridors) >= 1

    def test_corridor_direction(self):
        rt = RegionTracker()
        for i in range(MIGRATION_CORRIDOR_THRESHOLD + 2):
            rt.record_visit(2, 2, f"NPC{i}", i * 10)
            rt.record_visit(7, 7, f"NPC{i}", i * 10 + 5)
        corridors = rt.get_migration_corridors()
        corr = corridors[0]
        assert corr["from"] == "西北森林"
        assert corr["to"] == "中央平原"

    def test_corridor_report_not_empty_with_data(self):
        rt = RegionTracker()
        for i in range(MIGRATION_CORRIDOR_THRESHOLD + 5):
            rt.record_visit(2, 2, f"NPC{i}", i * 10)
            rt.record_visit(7, 7, f"NPC{i}", i * 10 + 5)
        report = rt.get_migration_corridor_report()
        assert "迁徙走廊" in report or "西北森林" in report


class TestMigrationFlow:
    """迁徙流向测试"""

    def test_net_flow_calculation(self):
        rt = RegionTracker()
        for i in range(MIGRATION_CORRIDOR_THRESHOLD + 2):
            rt.record_visit(2, 2, f"N{i}", i * 10)
            rt.record_visit(7, 7, f"N{i}", i * 10 + 5)
        flow = rt.get_migration_flow("nw_forest")
        assert flow["outflow"] != {}

    def test_inflow_tracking(self):
        rt = RegionTracker()
        # NPC 从 nw_forest → central_plain
        for i in range(MIGRATION_CORRIDOR_THRESHOLD + 2):
            rt.record_visit(2, 2, f"N{i}", i * 10)
            rt.record_visit(7, 7, f"N{i}", i * 10 + 5)
        flow = rt.get_migration_flow("central_plain")
        assert flow["inflow"] != {}


class TestGeoReport:
    """地理报告测试"""

    def test_observer_has_geo_report_property(self):
        from observer.world_observer import WorldObserver
        o = WorldObserver()
        assert hasattr(o, "last_geo_report")
        assert o.last_geo_report is None
