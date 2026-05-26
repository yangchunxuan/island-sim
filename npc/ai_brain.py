"""
AI决策层 — Island Sim v1 (T-028)

在关键时刻通过DeepSeek API获取高层决策建议。
架构：AI层为advisor，FSM为executor。AI建议行为，FSM执行。
AI离线时FSM可独立运行。
"""

import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Optional

from openai import OpenAI

from config import AI_CONFIG

# ── NPC人格profile ──

NPC_PROFILES: dict[str, str] = {
    "阿强": "你叫阿强，30岁男性，勤劳务实，喜欢探索和冒险。为人可靠但有时冲动。",
    "阿珍": "你叫阿珍，28岁女性，善良热心，乐于助人。稳重体贴，社区凝聚力强。",
    "大壮": "你叫大壮，35岁男性，力气大但比较懒，随遇而安。能帮忙搬重物但不爱主动做事。",
    "小美": "你叫小美，22岁女性，聪明好奇，对周围一切充满求知欲。爱学习爱探索新事物。",
    "老李": "你叫老李，55岁男性，经验丰富性格沉稳，是社区里的长者。做事慎重考虑周全。",
}

DECISION_TEMPLATE: str = """你是一个荒岛生存游戏的NPC角色。请基于以下信息做出行为决策。

{profile}

当前状态：
- 位置：({x}, {y})
- 饥饿值：{hunger}/100
- 能量值：{energy}/100
- 心情值：{mood}/100
- 当前行为：{state}

{context}

请从以下行为中选择一个最合适的（只回复一个词）：
- IDLE: 空闲休息
- WALK: 散步/移动
- SEARCH_FOOD: 寻找食物
- EAT: 进食
- SLEEP: 睡觉"""

_VALID_STATES: frozenset[str] = frozenset({"IDLE", "WALK", "SEARCH_FOOD", "EAT", "SLEEP"})


class AIBrain:
    """AI决策大脑，管理DeepSeek API调用和决策流程。

    通过线程池实现非阻塞调用，自带rate limit和fallback机制。
    """

    def __init__(self) -> None:
        self._client: OpenAI = OpenAI(
            api_key=str(AI_CONFIG["api_key"]),
            base_url=str(AI_CONFIG["base_url"]),
        )
        self._last_call_time: dict[str, float] = {}
        self._pending: dict[str, Future] = {}
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=int(AI_CONFIG["max_workers"]),  # type: ignore[arg-type]
        )

    def should_query(self, npc_name: str) -> bool:
        """检查是否允许向API发起请求（rate limit）。

        每NPC每rate_limit_seconds秒最多1次调用。
        """
        last = self._last_call_time.get(npc_name, 0.0)
        elapsed = time.time() - last
        return elapsed >= float(AI_CONFIG["rate_limit_seconds"])  # type: ignore[arg-type]

    def request_decision(self, npc: Any, context: Optional[dict] = None) -> bool:
        """发起异步决策请求（非阻塞）。

        Args:
            npc: NPC对象（需要name, x, y, hunger, energy, mood, get_state等属性）
            context: 补充上下文（可选键：nearby_npcs, idle_duration, event）

        Returns:
            True表示请求已发出，False表示被rate limit限制
        """
        if not self.should_query(npc.name):
            return False

        prompt = self._build_prompt(npc, context or {})

        future: Future = self._executor.submit(self._sync_call, prompt)
        self._pending[npc.name] = future
        self._last_call_time[npc.name] = time.time()
        return True

    def get_decision(self, npc_name: str) -> Optional[str]:
        """获取NPC的AI决策结果（非阻塞）。

        检查异步任务是否完成，完成则返回解析后的状态名，否则返回None。
        """
        future = self._pending.get(npc_name)
        if future is None:
            return None
        if not future.done():
            return None

        del self._pending[npc_name]
        try:
            raw: Optional[str] = future.result()
            return self._parse_response(raw)
        except Exception:
            return None  # fallback: API失败降级到纯FSM

    def _build_prompt(self, npc: Any, context: dict) -> str:
        """构建包含NPC完整上下文的prompt。"""
        profile = NPC_PROFILES.get(npc.name, f"你叫{npc.name}")

        # 获取NPC属性（兼容Mock和真实NPC）
        hunger = int(getattr(npc, "hunger", 50))
        energy = int(getattr(npc, "energy", 50))
        mood = int(getattr(npc, "mood", 50))
        state = npc.get_state() if hasattr(npc, "get_state") else "IDLE"

        extra_parts: list[str] = []
        if "nearby_npcs" in context:
            extra_parts.append(f"附近的NPC：{', '.join(context['nearby_npcs'])}")
        if "idle_duration" in context:
            extra_parts.append(f"已经空闲了{context['idle_duration']}秒")
        if "event" in context:
            extra_parts.append(f"发生的事件：{context['event']}")

        context_str = ""
        if extra_parts:
            context_str = "补充信息：\n" + "\n".join(extra_parts)

        return DECISION_TEMPLATE.format(
            profile=profile,
            x=npc.x,
            y=npc.y,
            hunger=hunger,
            energy=energy,
            mood=mood,
            state=state,
            context=context_str,
        )

    def _sync_call(self, prompt: str) -> Optional[str]:
        """同步调用DeepSeek API（在线程池中运行）。"""
        try:
            response = self._client.chat.completions.create(
                model=str(AI_CONFIG["model"]),
                messages=[{"role": "user", "content": prompt}],
                timeout=int(AI_CONFIG["timeout"]),  # type: ignore[arg-type]
                max_tokens=int(AI_CONFIG["max_tokens"]),  # type: ignore[arg-type]
            )
            return response.choices[0].message.content
        except Exception:
            return None

    @staticmethod
    def _parse_response(raw: Optional[str]) -> Optional[str]:
        """从AI响应中解析出建议的行为状态名。"""
        if not raw:
            return None
        upper = raw.strip().upper()
        for state in _VALID_STATES:
            if state in upper:
                return state
        return None

    def shutdown(self) -> None:
        """释放线程池资源。"""
        self._executor.shutdown(wait=False)
