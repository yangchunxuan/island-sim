"""
世界观察者 — Island Sim v1

统一观察入口。每帧轮询游戏状态，检测变化并记录事件。
T-027: 新增地理生态报告（地力/气候/迁徙/避难所）。
"""

from typing import Any, Optional

from config import GEO_REPORT_INTERVAL
from observer.event_formatter import EventFormatter
from observer.event_logger import EventLogger
from observer.event_stream import EventStream
from observer.event_trace import EventTrace
from observer.evidence_system import EvidenceSystem
from observer.live_feed import LiveFeed
from observer.long_term_memory import LongTermMemory
from observer.pattern_analyzer import PatternAnalyzer
from observer.narrative_generator import NarrativeGenerator
from observer.pressure_tracker import PressureTracker
from observer.region_tracker import RegionTracker
from observer.world_chronicle import WorldChronicle


def _region_name(x: int, y: int) -> str:
    """将坐标映射到地理区域名称"""
    if x < 10 and y < 10:
        return "西北"
    if x >= 10 and y < 10:
        return "东北"
    if x < 10 and y >= 10:
        return "西南"
    return "东南"


class WorldObserver:
    """世界观察者。轮询状态、检测变化、记录事件、分析模式、生成叙事。"""

    ANALYSIS_INTERVAL: int = 1200  # 每1200tick分析一次

    def __init__(self) -> None:
        self.event_logger = EventLogger()
        self._analyzer = PatternAnalyzer(self.event_logger)
        self._narrator = NarrativeGenerator()
        self._prev_npc_state: dict[int, dict[str, Any]] = {}
        self._prev_depleted: set[tuple[int, int]] = set()
        self._prev_mushrooms: dict[tuple[int, int], int] = {}
        self._prev_fish: dict[tuple[int, int], int] = {}
        self._last_analysis_tick: int = 0
        self._last_report: Optional[dict[str, Any]] = None
        self._pressure_map: object = None
        self._memory: LongTermMemory = LongTermMemory()
        self._chronicle: WorldChronicle = WorldChronicle()
        self._event_stream: EventStream = EventStream()
        self._formatter: EventFormatter = EventFormatter()
        self._live_feed: LiveFeed = LiveFeed()
        self._region_tracker: RegionTracker = RegionTracker()
        self._pressure_tracker: PressureTracker = PressureTracker()
        self._event_trace: EventTrace = EventTrace()
        self._evidence_system: EvidenceSystem = EvidenceSystem()
        self._last_formatted_tick: int = 0
        self._last_trace_tick: int = 0
        self._last_pressure_record_tick: int = 0
        self._prev_depletion_count: int = 0
        self._prev_recovery_count: int = 0
        self._last_geo_report_tick: int = 0
        self._last_geo_report: Optional[str] = None

    def set_pressure_map(self, pressure_map: object) -> None:
        """注入区域压力图引用"""
        self._pressure_map = pressure_map

    def _log_npc_profiles(self, tick: int, npcs: list) -> None:
        """记录每个NPC的行为倾向配置（首次检测时记录一次）"""
        if not hasattr(self, '_profile_logged'):
            self._profile_logged = set()
        for npc in npcs:
            name = getattr(npc, "name", "Unknown")
            if name in self._profile_logged:
                continue
            self._profile_logged.add(name)
            self.event_logger.log(
                tick, "NPC_BEHAVIOR_PROFILE",
                npc=name,
                details={
                    "risk_tolerance": round(getattr(npc, "risk_tolerance", 0.5), 2),
                    "laziness": round(getattr(npc, "laziness", 0.5), 2),
                    "food_preference": round(getattr(npc, "food_preference", 0.5), 2),
                    "exploration_bias": round(getattr(npc, "exploration_bias", 0.5), 2),
                },
            )

    def update(
        self,
        tick: int,
        resource_mgr: object,
        npcs: list,
    ) -> None:
        """主更新入口：检测变化 → 记录事件 → 事件流 → 定期分析"""
        self._log_npc_profiles(tick, npcs)
        if resource_mgr is not None:
            self._detect_resource_events(tick, resource_mgr)
        self._detect_npc_events(tick, npcs)

        # 区域压力事件 → 日志 + 区域追踪
        pm = self._pressure_map
        if pm is not None and resource_mgr is not None:
            for ev_type, region in pm.update(tick, resource_mgr):
                rrx, rry = region  # region coords (0-3)
                # 区域坐标转tile坐标用于日志
                tile_pos = (rrx * 5 + 2, rry * 5 + 2)
                self.event_logger.log(tick, ev_type, position=tile_pos)
                if ev_type == "REGION_COLLAPSE":
                    self._region_tracker.record_collapse_at_grid(rrx, rry)
                if ev_type == "REGION_RECOVERY":
                    pass  # recovery tracked via FOREST_RECOVERED
                self._region_tracker.update_pressure_at_grid(
                    rrx, rry,
                    pm.get_score(rrx, rry),
                )

        if resource_mgr is not None:
            self._update_resource_snapshot(resource_mgr)
        self._update_npc_snapshot(npcs)

        # 事件流输出（每次update追加新事件）
        self._event_stream.update(tick, self.event_logger)
        # 编年史：每帧检查是否有新里程碑事件
        self._chronicle.update(tick, self.event_logger)

        # 实时叙事流：新事件格式化 → live_feed
        self._update_live_feed(tick, resource_mgr, npcs)

        # 压力趋势追踪（每120tick）
        if tick - self._last_pressure_record_tick >= 120 and tick > 0:
            self._last_pressure_record_tick = tick
            self._update_pressure_tracker(resource_mgr, npcs)

        if tick - self._last_analysis_tick >= self.ANALYSIS_INTERVAL and tick > 0:
            self._last_analysis_tick = tick
            self._run_analysis(tick, npcs, resource_mgr)

        # 地理生态报告（每2400tick）
        if tick - self._last_geo_report_tick >= GEO_REPORT_INTERVAL and tick > 0:
            self._last_geo_report_tick = tick
            self._generate_geo_report(tick, resource_mgr, npcs)

    def _run_analysis(
        self,
        tick: int,
        npcs: list,
        resource_mgr: object,
    ) -> None:
        """执行模式分析和叙事生成，同时更新长期记忆"""
        report = self._analyzer.analyze(tick, npcs, resource_mgr)
        self._memory.update(tick, npcs, self._pressure_map)
        report["world_history"] = self._memory.get_summary()
        self._last_report = report
        self._narrator.generate(tick, report)

    # ── 地理生态报告（T-027） ──

    def _generate_geo_report(
        self,
        tick: int,
        resource_mgr: object,
        npcs: list,
    ) -> None:
        """生成地理生态分析报告：地力/气候/迁徙/避难所"""
        pm = self._pressure_map
        if pm is None:
            return

        lines: list[str] = []
        report_data: dict[str, Any] = {}

        # ── 地力报告 ──
        fert_data = pm.get_fertility_report()
        report_data["fertility"] = fert_data
        high_fert = [f for f in fert_data if f["current_fertility"] >= 0.65]
        low_fert = [f for f in fert_data if f["current_fertility"] <= 0.25]
        declining = [f for f in fert_data if f["trend"] == "declining"]
        increasing = [f for f in fert_data if f["trend"] == "increasing"]

        if high_fert:
            names = "、".join(f["name"] for f in high_fert[:3])
            lines.append(f"[GEOGRAPHY] 富饶区：{names} 地力稳定")
            self._log_geo_event(tick, "GEO_FERTILE_REGION", high_fert[:3])
        if low_fert:
            names = "、".join(f["name"] for f in low_fert[:3])
            lines.append(f"[GEOGRAPHY] 贫瘠区：{names} 地力严重下降")
            self._log_geo_event(tick, "GEO_BARREN_REGION", low_fert[:3])
        if declining:
            names = "、".join(f["name"] for f in declining[:3])
            lines.append(f"[GEOGRAPHY] 地力下降区：{names}")
        if increasing:
            names = "、".join(f["name"] for f in increasing[:3])
            lines.append(f"[GEOGRAPHY] 地力恢复区：{names}")

        # ── 气候报告 ──
        climate_data = pm.get_climate_report()
        report_data["climate"] = climate_data
        humid_regions = [c for c in climate_data if c["type"] == "humid"]
        arid_regions = [c for c in climate_data if c["type"] == "arid"]
        if humid_regions:
            names = "、".join(c["name"] for c in humid_regions)
            lines.append(f"[CLIMATE] 湿润区：{names} — 蘑菇资源丰富")
        if arid_regions:
            names = "、".join(c["name"] for c in arid_regions)
            lines.append(f"[CLIMATE] 干旱区：{names} — 恢复速度受限")

        # ── 生态避难所 ──
        refugia = pm.get_refugia_list()
        report_data["refugia"] = refugia
        if refugia:
            names = "、".join(refugia)
            lines.append(f"[ECOLOGY] 生态避难所：{names} — 恢复核心区")
            self._log_geo_event(tick, "GEO_REFUGIA_ACTIVE", refugia)

        # ── 迁徙走廊 ──
        corridors = self._region_tracker.get_migration_corridors()
        report_data["migration_corridors"] = corridors
        if corridors:
            for c in corridors[:3]:
                lines.append(
                    f"[MIGRATION] 迁徙走廊：{c['from']} → {c['to']} ({c['traffic']} 次)"
                )
                self._log_geo_event(tick, "GEO_MIGRATION_CORRIDOR", c)
        else:
            lines.append("[MIGRATION] 尚未形成稳定迁徙走廊")

        # ── 空间生态 ──
        collapsed = pm.collapsed_regions
        report_data["collapsed_regions"] = list(collapsed)
        if collapsed:
            collapsed_names = []
            for rx, ry in collapsed:
                name = pm.region_name(rx, ry)
                collapsed_names.append(name)
            if collapsed_names:
                lines.append(
                    f"[ECOLOGY] 崩溃区：{'、'.join(collapsed_names)} — 生态压力正在传播"
                )

        # 压力最高的区域
        top_pressure = pm.get_top_pressure(3)
        report_data["top_pressure"] = top_pressure
        pressure_lines = []
        for (rx, ry), score in top_pressure:
            name = pm.region_name(rx, ry)
            pressure_lines.append(f"{name}({score:.2f})")
        if pressure_lines:
            lines.append(
                f"[GEOGRAPHY] 高压力区：{' > '.join(pressure_lines)}"
            )

        report_text = "\n".join(lines)
        self._last_geo_report = report_text

        # 记录到事件日志（取重要信息推入实时流）
        if lines:
            self.event_logger.log(
                tick, "GEOGRAPHY_REPORT",
                details=report_data,
            )

    def _log_geo_event(
        self, tick: int, ev_type: str, data: Any,
    ) -> None:
        """记录地理事件到事件日志（确保 details 为 dict）"""
        if isinstance(data, dict):
            detail_dict = data
        elif isinstance(data, list):
            detail_dict = {"items": data}
        else:
            detail_dict = {"value": str(data)}
        self.event_logger.log(tick, ev_type, details=detail_dict)

    # ── 资源事件检测 ──

    def _detect_resource_events(
        self,
        tick: int,
        resource_mgr: object,
    ) -> None:
        """轮询资源管理器，检测资源变化"""
        current_depleted = set(resource_mgr.depleted_forests)
        current_mushrooms = dict(resource_mgr.mushrooms)
        current_fish = dict(resource_mgr.fish)

        # 森林恢复
        recovered = self._prev_depleted - current_depleted
        for pos in recovered:
            self.event_logger.log(
                tick, "FOREST_RECOVERED",
                position=pos,
                details={"from": "depleted", "to": "active"},
            )

        # 资源耗尽
        newly_depleted = current_depleted - self._prev_depleted
        for pos in newly_depleted:
            self.event_logger.log(
                tick, "RESOURCE_DEPLETED",
                position=pos,
                details={"type": "forest"},
            )
            self._region_tracker.record_depletion(pos[0], pos[1], "forest")

        # 森林恢复
        for pos in recovered:
            self._region_tracker.record_recovery(pos[0], pos[1])

        # 蘑菇生成
        for pos in current_mushrooms:
            if pos not in self._prev_mushrooms:
                self.event_logger.log(
                    tick, "MUSHROOM_SPAWN",
                    position=pos,
                    details=current_mushrooms[pos],
                )

        # 鱼生成
        for pos in current_fish:
            if pos not in self._prev_fish:
                self.event_logger.log(
                    tick, "FISH_SPAWN",
                    position=pos,
                    details=current_fish[pos],
                )

    # ── NPC事件检测 ──

    def _detect_npc_events(self, tick: int, npcs: list) -> None:
        """轮询NPC状态，检测行为变化"""
        for idx, npc in enumerate(npcs):
            prev = self._prev_npc_state.get(idx, {})
            current_state = npc.get_state()
            current_x = int(getattr(npc, "x", 0))
            current_y = int(getattr(npc, "y", 0))
            current_weakened = bool(getattr(npc, "_weakened", False))
            current_hunger = int(getattr(npc, "hunger", 0))
            name = getattr(npc, "name", "Unknown")

            # 首次记录跳过（无prev数据）
            if not prev:
                self._prev_npc_state[idx] = {
                    "state": current_state,
                    "x": current_x,
                    "y": current_y,
                    "weakened": current_weakened,
                    "hunger": current_hunger,
                }
                continue

            # Weakened状态变化
            if current_weakened and not prev.get("weakened"):
                self.event_logger.log(
                    tick, "NPC_ENTER_WEAKENED",
                    npc=name,
                    position=(current_x, current_y),
                    details={"hunger": current_hunger},
                )
            elif not current_weakened and prev.get("weakened"):
                self.event_logger.log(
                    tick, "NPC_RECOVER_WEAKENED",
                    npc=name,
                    position=(current_x, current_y),
                    details={"hunger": current_hunger},
                )

            # 饮食事件：状态从EAT切换到其他
            if prev.get("state") == "EAT" and current_state != "EAT":
                hunger_drop = prev.get("hunger", current_hunger) - current_hunger
                if hunger_drop > 0:
                    self.event_logger.log(
                        tick, "NPC_EAT",
                        npc=name,
                        position=(current_x, current_y),
                        details={"hunger_drop": hunger_drop},
                    )

            # 睡眠事件：状态进入SLEEP
            if current_state == "SLEEP" and prev.get("state") != "SLEEP":
                self.event_logger.log(
                    tick, "NPC_SLEEP",
                    npc=name,
                    position=(current_x, current_y),
                    details={"energy": int(getattr(npc, "energy", 0))},
                )

            # 区域移动
            prev_x, prev_y = prev.get("x", current_x), prev.get("y", current_y)
            prev_region = _region_name(prev_x, prev_y)
            curr_region = _region_name(current_x, current_y)
            if prev_region != curr_region:
                self.event_logger.log(
                    tick, "NPC_MOVE_REGION",
                    npc=name,
                    position=(current_x, current_y),
                    details={"from": prev_region, "to": curr_region},
                )
                self._region_tracker.record_visit(
                    current_x, current_y, name, tick,
                )

    # ── 快照更新 ──

    def _update_resource_snapshot(
        self,
        resource_mgr: object,
    ) -> None:
        """更新资源快照"""
        self._prev_depleted = set(resource_mgr.depleted_forests)
        self._prev_mushrooms = dict(resource_mgr.mushrooms)
        self._prev_fish = dict(resource_mgr.fish)

    def _update_npc_snapshot(
        self,
        npcs: list,
    ) -> None:
        """更新NPC快照"""
        for idx, npc in enumerate(npcs):
            self._prev_npc_state[idx] = {
                "state": npc.get_state(),
                "x": int(getattr(npc, "x", 0)),
                "y": int(getattr(npc, "y", 0)),
                "weakened": bool(getattr(npc, "_weakened", False)),
                "hunger": int(getattr(npc, "hunger", 0)),
            }

    # ── 实时叙事流 + 事件追踪 + 证据链 ──

    def _update_live_feed(
        self,
        tick: int,
        resource_mgr: object = None,
        npcs: list = None,
    ) -> None:
        """将新事件格式化后推入实时流，同时追踪事件和收集证据"""
        events = self.event_logger.get_events_since(self._last_formatted_tick)
        for ev in events:
            if ev["tick"] > self._last_formatted_tick:
                # 事件追踪
                event_id = self._event_trace.register(ev)

                # 证据收集
                evidence = self._collect_event_evidence(ev, resource_mgr, npcs)
                if evidence:
                    self._evidence_system.store(event_id, evidence)

                # 置信度计算
                confidence = self._evidence_system.compute_confidence(
                    ev["event_type"], evidence,
                )

                # 跳过ECOLOGY事件（避免淹没实时流）
                level = self._formatter.get_level(ev)
                if level == "ECOLOGY":
                    continue

                # 格式化并推入实时流
                meta = self._formatter.format_with_meta(
                    ev, event_id, confidence,
                    self._evidence_system.get_evidence_preview(event_id),
                )
                self._live_feed.append(
                    ev["tick"], meta["level"], meta["message"],
                    event_id=meta["event_id"],
                    confidence=meta["confidence"],
                    region=meta["region"],
                    evidence_preview=meta["evidence_preview"],
                )
        if events:
            self._last_formatted_tick = max(e["tick"] for e in events)

    def _collect_event_evidence(
        self,
        event: dict,
        resource_mgr: object = None,
        npcs: list = None,
    ) -> dict:
        """收集事件的上下文证据"""
        ev_type = event.get("event_type", "")
        npc_name = event.get("npc")
        pos = event.get("position")

        if npc_name and npcs:
            for n in npcs:
                if getattr(n, "name", "") == npc_name:
                    return self._evidence_system.collect_npc_evidence(
                        n, resource_mgr, self._pressure_map,
                    )
        if ev_type in ("RESOURCE_DEPLETED", "FOREST_RECOVERED",
                       "REGION_COLLAPSE", "REGION_RECOVERY"):
            if pos and len(pos) == 2 and resource_mgr is not None:
                return self._evidence_system.collect_resource_evidence(
                    pos[0], pos[1], resource_mgr,
                )
        return {}

    # ── 压力趋势追踪 ──

    def _update_pressure_tracker(
        self,
        resource_mgr: object,
        npcs: list,
    ) -> None:
        """定期记录压力数据点"""
        depletion_count = self._region_tracker.get_all_stats()
        total_dep = sum(
            s["depletions"] for s in depletion_count.values()
        ) if depletion_count else 0
        total_rec = sum(
            s["recoveries"] for s in depletion_count.values()
        ) if depletion_count else 0
        delta_dep = total_dep - self._prev_depletion_count
        delta_rec = total_rec - self._prev_recovery_count
        self._prev_depletion_count = total_dep
        self._prev_recovery_count = total_rec
        self._pressure_tracker.record(0, npcs, delta_dep, delta_rec)

    # ── 公开属性 ──

    @property
    def last_report(self) -> Optional[dict[str, Any]]:
        """返回最近一次分析报告"""
        return self._last_report

    @property
    def live_feed(self) -> LiveFeed:
        return self._live_feed

    @property
    def region_tracker(self) -> RegionTracker:
        return self._region_tracker

    @property
    def pressure_tracker(self) -> PressureTracker:
        return self._pressure_tracker

    @property
    def event_trace(self) -> EventTrace:
        return self._event_trace

    @property
    def evidence_system(self) -> EvidenceSystem:
        return self._evidence_system

    @property
    def last_geo_report(self) -> Optional[str]:
        """返回最近一次地理生态报告"""
        return self._last_geo_report
