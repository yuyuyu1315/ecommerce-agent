"""Agent 基类：统一 LLM 构建、JSON/文本调用、任务记录与调用计时"""
import json
import time
from typing import Any, Dict, Optional, Tuple

from langchain_openai import ChatOpenAI

from backend.config import get_settings


def extract_json(text: str) -> Dict[str, Any]:
    """从 LLM 输出中稳健提取 JSON 对象（支持代码块围栏与前后缀文本）"""
    if not text:
        raise ValueError("LLM 返回为空")
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError(f"无法解析 LLM JSON 输出: {text[:200]}")


def _usage_of(response) -> Optional[Dict[str, int]]:
    """从 LangChain 响应中提取 token 用量（兼容不同版本）"""
    usage = getattr(response, "usage_metadata", None)
    if usage and isinstance(usage, dict):
        return {
            "input_tokens": usage.get("input_tokens") or 0,
            "output_tokens": usage.get("output_tokens") or 0,
            "total_tokens": usage.get("total_tokens") or 0,
        }
    meta = getattr(response, "response_metadata", {}) or {}
    token_usage = meta.get("token_usage") or {}
    if token_usage:
        return {
            "input_tokens": token_usage.get("prompt_tokens") or 0,
            "output_tokens": token_usage.get("completion_tokens") or 0,
            "total_tokens": token_usage.get("total_tokens") or 0,
        }
    return None


class BaseAgent:
    """所有 Agent 的基类：统一 LLM（JSON 模式与自由文本模式）"""

    name: str = "BaseAgent"
    default_system_prompt: str = "你是一个专业的电商运营助手，请用 JSON 返回结果。"

    def __init__(self):
        self.settings = get_settings()
        self.llm = self._build_llm(require_json=True)
        self.text_llm = self._build_llm(require_json=False)

    def _build_llm(self, require_json: bool = True) -> ChatOpenAI:
        api_key = self.settings.OPENAI_API_KEY
        if not api_key or "xxxx" in api_key:
            raise RuntimeError("OPENAI_API_KEY 未配置，请在 .env 中填写 DeepSeek Key")
        kwargs: Dict[str, Any] = dict(
            model=self.settings.OPENAI_MODEL,
            api_key=api_key,
            base_url=self.settings.OPENAI_BASE_URL,
            temperature=self.settings.LLM_TEMPERATURE,
            timeout=120,
            max_retries=2,
        )
        if require_json:
            kwargs["response_format"] = {"type": "json_object"}
        return ChatOpenAI(**kwargs)

    async def ainvoke_json(
        self, system_prompt: str, user_prompt: str
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, int]]]:
        """调用 LLM（JSON 模式），返回 (解析后的 dict, token 用量)"""
        start = time.perf_counter()
        response = await self.llm.ainvoke(
            [
                ("system", system_prompt),
                ("human", user_prompt),
            ]
        )
        parsed = extract_json(response.content)
        parsed["_meta"] = {"duration_ms": int((time.perf_counter() - start) * 1000)}
        return parsed, _usage_of(response)

    async def ainvoke_text(
        self, system_prompt: str, user_prompt: str
    ) -> Tuple[str, Optional[Dict[str, int]]]:
        """调用 LLM（自由文本模式），返回 (回答文本, token 用量)"""
        start = time.perf_counter()
        response = await self.text_llm.ainvoke(
            [
                ("system", system_prompt),
                ("human", user_prompt),
            ]
        )
        return str(response.content).strip(), _usage_of(response)
