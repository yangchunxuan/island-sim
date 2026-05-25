"""
叙事生成器 — Island Sim v1

规则模板驱动的世界叙事生成。严格基于真实数据，禁止LLM/编造。
输出结构化世界日报：区域分析 / NPC行为 / 资源趋势 / 世界压力 / 世界历史。
"""

import os
from typing import Any

REPORT_DIR: str = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "world_reports"
)

SEP: str = "─" * 40


class NarrativeGenerator:
    """世界叙事生成器。将模式分析报告转为结构化日报。"""

    def __init__(self) -> None:
        os.makedirs(REPORT_DIR, exist_ok=True)

    def generate(
        self,
        tick: int,
        pattern_report: dict[str, Any],
    ) -> str:
        """根据模式分析报告生成当日结构化日报。返回完整文本。"""
        day = pattern_report["day"]
        sections: list[str] = [f"Day {day}", SEP]

        # ── 区域分析 ──
        sections.append(self._render_region_analysis(pattern_report))

        # ── NPC行为分析 ──
        sections.append(self._render_npc_analysis(pattern_report))

        # ── 资源趋势 ──
        sections.append(self._render_resource_trends(pattern_report))

        # ── 世界压力 ──
        sections.append(self._render_world_pressure(pattern_report))

        # ── 世界历史（长期记忆） ──
        wh = pattern_report.get("world_history", {})
        if wh.get("days_simulated", 0) > 1:
            sections.append(self._render_world_history(wh))

        report_text = "\n".join(sections)
        self._write_report(day, report_text)
        return report_text

    # ── 各板块渲染 ──

    def _render_region_analysis(self, report: dict[str, Any]) -> str:
        """区域分析：高压区 / 恢复区 / 冷清区"""
        lines: list[str] = ["═══ 区域分析 ═══"]
        hot_regions = report.get("hot_regions", [])

        # 高压区（活动最频繁的）
        pressure = report.get("world_history", {}).get("most_dangerous_region", "")
        if hot_regions:
            hottest = hot_regions[0]
            activity_pct = int(hottest["ratio"] * 100)
            lines.append(f"热点: {hottest['name']}（活动占比{activity_pct}%）")

        # 冷清区
        if len(hot_regions) >= 2:
            coldest = hot_regions[-1]
            if coldest["ratio"] < 0.15:
                lines.append(f"冷清: {coldest['name']}（活动占比仅{int(coldest['ratio']*100)}%）")

        # 崩溃区
        if pressure and pressure != "无记录":
            lines.append(f"高危: {pressure}")

        if len(lines) == 1:
            lines.append("各区域活动水平均衡。")
        return "\n".join(lines)

    def _render_npc_analysis(self, report: dict[str, Any]) -> str:
        """NPC行为分析：状态 / 倾向 / 生存状况"""
        lines: list[str] = ["═══ NPC行为分析 ═══"]
        tendencies = report.get("npc_tendencies", [])
        wh = report.get("world_history", {})
        npc_days = wh.get("npc_days", {})

        for npc in tendencies:
            name = npc["name"]
            parts = [f"{name}:"]
            parts.append(f"状态={npc['state']}")
            parts.append(f"饥饿={npc['hunger']}")
            parts.append(f"情绪={npc['mood']}")

            if npc.get("weakened"):
                parts.append("⚠虚弱")
            if npc.get("coastal_tendency"):
                parts.append("偏好海岸")
            if npc.get("recent_moves", 0) > 5:
                parts.append("高频迁徙")

            survival = npc_days.get(name, 0)
            if survival > 0:
                parts.append(f"存活{survival}天")

            lines.append("  ".join(parts))

        if not tendencies:
            lines.append("暂无NPC活动数据。")
        return "\n".join(lines)

    def _render_resource_trends(self, report: dict[str, Any]) -> str:
        """资源趋势：森林 / 蘑菇 / 鱼"""
        lines: list[str] = ["═══ 资源趋势 ═══"]
        rt = report.get("resource_trends", {})

        total_food = rt.get("total_food", 0)
        depleted = rt.get("depleted_count", 0)
        depletion_rate = rt.get("depletion_rate", 0)
        mushroom = rt.get("mushroom_activity", 0)
        fish = rt.get("fish_activity", 0)
        recovery = rt.get("recovery_active", False)

        lines.append(f"森林食物存量: {total_food}（{depleted}处枯竭，枯竭率{int(depletion_rate*100)}%）")
        if recovery:
            lines.append("生态恢复: 部分森林正在恢复。")

        if mushroom > 0 or fish > 0:
            lines.append(f"替代食物源: 蘑菇生成{mushroom}处，鱼生成{fish}处。")
        else:
            lines.append("替代食物源: 近期无蘑菇/鱼生成。")

        return "\n".join(lines)

    def _render_world_pressure(self, report: dict[str, Any]) -> str:
        """世界压力：平均属性 / 虚弱NPC"""
        lines: list[str] = ["═══ 世界压力 ═══"]
        wp = report.get("world_pressure", {})

        avg_hunger = wp.get("avg_hunger", 0)
        avg_energy = wp.get("avg_energy", 0)
        avg_mood = wp.get("avg_mood", 0)
        w_count = wp.get("weakened_count", 0)

        lines.append(f"平均饥饿={avg_hunger}  平均体力={avg_energy}  平均情绪={avg_mood}")
        if w_count > 0:
            lines.append(f"当前虚弱NPC: {w_count}人")
        else:
            lines.append("当前无NPC处于虚弱状态。")

        # 总体评估
        if w_count >= 2:
            lines.append("评估: 世界生存压力上升中。")
        elif avg_hunger > 50:
            lines.append("评估: 食物供给偏紧。")
        elif avg_hunger < 20 and avg_mood > 60:
            lines.append("评估: 世界状态良好。")

        return "\n".join(lines)

    def _render_world_history(self, wh: dict[str, Any]) -> str:
        """世界历史摘要（基于长期记忆）"""
        lines = ["═══ 世界历史 ═══"]
        days = wh.get("days_simulated", 0)
        lines.append(f"模拟天数: {days}天")

        if wh.get("all_time_max_hunger", 0) > 0:
            lines.append(
                f"历史最高饥饿: {wh['all_time_max_hunger']}（{wh['all_time_max_hunger_npc']}）"
            )
        if wh.get("total_collapses", 0) > 0:
            lines.append(
                f"区域崩溃: 共{wh['total_collapses']}次，最危险区域{wh['most_dangerous_region']}"
            )
        if wh.get("avg_mood_long_term", 50):
            lines.append(f"长期平均情绪: {wh['avg_mood_long_term']}")

        return "\n".join(lines)

    # ── 文件写入 ──

    def _write_report(self, day: int, text: str) -> None:
        """写入world_reports/day_{day}.md"""
        path = os.path.join(REPORT_DIR, f"day_{day:03d}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text + "\n")

    def get_report_path(self, day: int) -> str:
        return os.path.join(REPORT_DIR, f"day_{day:03d}.md")

    def report_exists(self, day: int) -> bool:
        return os.path.exists(self.get_report_path(day))
