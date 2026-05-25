"""
叙事生成器 — Island Sim v1

规则模板驱动的世界叙事生成。严格基于真实数据，禁止LLM/编造。
"""

import os
from typing import Any

REPORT_DIR: str = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "world_reports"
)


class NarrativeGenerator:
    """世界叙事生成器。将模式分析报告转为规则模板叙事。"""

    def __init__(self) -> None:
        os.makedirs(REPORT_DIR, exist_ok=True)

    def generate(
        self,
        tick: int,
        pattern_report: dict[str, Any],
    ) -> str:
        """根据模式分析报告生成当日叙事。返回完整文本。"""
        lines: list[str] = []
        day = pattern_report["day"]

        # ── 资源热点 ──
        hot_regions = pattern_report.get("hot_regions", [])
        if hot_regions:
            hottest = hot_regions[0]
            lines.append(f"{hottest['name']}仍然是主要资源热点。")

        # ── 资源趋势 ──
        rt = pattern_report.get("resource_trends", {})
        if rt.get("recovery_active"):
            lines.append("部分森林生态开始恢复。")
        if rt.get("depletion_rate", 0) > 0.5:
            lines.append("部分区域出现长期枯竭。")
        elif rt.get("depletion_rate", 0) > 0.3:
            lines.append("北方森林恢复速度下降。")

        # ── NPC个体观察 ──
        npc_tendencies = pattern_report.get("npc_tendencies", [])
        for npc in npc_tendencies:
            if npc.get("coastal_tendency"):
                lines.append(f"{npc['name']}逐渐形成海岸觅食路线。")
            if npc.get("weakened"):
                lines.append(f"{npc['name']}近期多次进入虚弱状态。")

        # ── 世界压力 ──
        wp = pattern_report.get("world_pressure", {})
        w_count = wp.get("weakened_count", 0)
        avg_hunger = wp.get("avg_hunger", 0)
        if w_count >= 2:
            lines.append("近期 weakened NPC 数量略有增加。")
            lines.append("岛屿整体生存压力正在上升。")
        elif avg_hunger > 50:
            lines.append("NPC群体平均饥饿水平偏高。")
        elif avg_hunger < 20:
            lines.append("NPC群体整体状态良好。")

        # ── 冷清区域 ──
        if len(hot_regions) >= 2:
            coldest = hot_regions[-1]
            if coldest["ratio"] < 0.15:
                lines.append(f"{coldest['name']}活动频率明显偏低。")

        # ── 世界历史（长期记忆） ──
        wh = pattern_report.get("world_history", {})
        if wh.get("days_simulated", 0) > 1:
            history_lines = []
            days = wh["days_simulated"]
            history_lines.append(f"自模拟启动以来共度过{days}天。")
            if wh["all_time_max_hunger"] > 0:
                history_lines.append(
                    f"历史最高饥饿值{wh['all_time_max_hunger']}（{wh['all_time_max_hunger_npc']}）。"
                )
            if wh["total_collapses"] > 0:
                history_lines.append(
                    f"共发生{wh['total_collapses']}次区域生态崩溃，"
                    f"最危险区域{wh['most_dangerous_region']}。"
                )
            if wh.get("avg_mood_long_term", 50) < 40:
                history_lines.append("群体长期情绪偏低。")
            elif wh.get("avg_mood_long_term", 50) > 70:
                history_lines.append("群体长期情绪保持良好。")
            lines.append("[世界历史] " + " ".join(history_lines))

        report_text = "\n".join(lines) if lines else "今日无显著事件发生。"
        self._write_report(day, report_text)
        return report_text

    def _write_report(self, day: int, text: str) -> None:
        """写入world_reports/day_{day}.md"""
        path = os.path.join(REPORT_DIR, f"day_{day:03d}.md")
        content = f"Day {day}\n{text}\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def get_report_path(self, day: int) -> str:
        """返回指定天的报告路径"""
        return os.path.join(REPORT_DIR, f"day_{day:03d}.md")

    def report_exists(self, day: int) -> bool:
        """指定天的报告是否已生成"""
        return os.path.exists(self.get_report_path(day))
