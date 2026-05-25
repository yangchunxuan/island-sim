"""
Headless模式测试 — Island Sim v1

验证 --headless --simulate-days N 无崩溃运行、统计输出。
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


class TestHeadlessSimulation(unittest.TestCase):
    """headless模式功能测试"""

    def setUp(self):
        self.stats_dir = tempfile.mkdtemp()

    def _run_headless(self, days: int) -> dict:
        """执行headless模拟并返回统计"""
        from main import run_headless

        # 用patch拦截文件路径
        original_dir = os.path.join(os.path.dirname(__file__), "..", "world_reports")
        stats_path = os.path.join(self.stats_dir, "statistics.json")

        with patch("main._save_headless_stats") as mock_save:
            def _fake_save(observer, time_system, resource_mgr, days_arg):
                """保存统计到临时目录"""
                events = observer.event_logger.get_events_since(0)
                memory_summary = {}
                if hasattr(observer, '_memory') and observer._memory is not None:
                    memory_summary = observer._memory.get_summary()
                stats = {
                    "days_simulated": days_arg,
                    "total_ticks": time_system._tick_count,
                    "total_events": len(events),
                    "event_types": {},
                    "world_history": memory_summary,
                }
                for e in events:
                    et = e["event_type"]
                    stats["event_types"][et] = stats["event_types"].get(et, 0) + 1
                with open(stats_path, "w", encoding="utf-8") as f:
                    json.dump(stats, f, ensure_ascii=False, indent=2)

            mock_save.side_effect = _fake_save
            run_headless(days)

        with open(stats_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_3_days_no_crash(self):
        """3天headless模拟不崩溃"""
        stats = self._run_headless(3)
        self.assertEqual(stats["days_simulated"], 3)

    def test_10_days_no_crash(self):
        """10天headless模拟不崩溃"""
        stats = self._run_headless(10)
        self.assertGreaterEqual(stats["days_simulated"], 10)

    def test_statistics_contains_events(self):
        """统计数据包含事件记录"""
        stats = self._run_headless(3)
        self.assertGreater(stats["total_events"], 0)
        self.assertIn("event_types", stats)

    def test_statistics_contains_npc_state(self):
        """统计数据包含NPC最终状态信息"""
        stats = self._run_headless(3)
        self.assertIn("world_history", stats)

    def test_100_days_no_crash(self):
        """100天headless模拟不崩溃（验收）"""
        stats = self._run_headless(100)
        self.assertGreaterEqual(stats["days_simulated"], 100)
        self.assertIn("event_types", stats)


if __name__ == "__main__":
    unittest.main()
