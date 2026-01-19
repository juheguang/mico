"""
DeepSeek Provider - 带超时和重试机制
"""

from __future__ import annotations
import os
import asyncio
from typing import AsyncIterator

from .base import BaseLLMProvider, StreamChunk, LLMConfig, DEFAULT_LLM_CONFIG


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek Provider (使用 OpenAI 兼容 API)"""

    DEEPSEEK_BASE_URL = "https://api.deepseek.com"

    # 不支持 function calling 的模型
    NO_TOOLS_MODELS = ["deepseek-reasoner"]

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = "deepseek-chat",
        config: LLMConfig = None
    ):
        from openai import AsyncOpenAI

        self.model = model
        self.config = config or DEFAULT_LLM_CONFIG
        self.client = AsyncOpenAI(
            api_key=api_key or os.getenv("DEEPSEEK_API_KEY"),
            base_url=base_url or os.getenv("DEEPSEEK_BASE_URL", self.DEEPSEEK_BASE_URL),
            timeout=self.config.timeout,
            max_retries=0
        )

    def _supports_tools(self) -> bool:
        """检查当前模型是否支持 tools"""
        return self.model not in self.NO_TOOLS_MODELS

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = None,
    ) -> AsyncIterator[StreamChunk]:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
        }

        # deepseek-reasoner 不支持 temperature 参数
        if self.model not in self.NO_TOOLS_MODELS:
            kwargs["temperature"] = temperature

        # deepseek-reasoner 不支持 tools
        if tools and self._supports_tools():
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        timeout = timeout or self.config.timeout
        last_error = None

        # 重试循环
        for attempt in range(self.config.max_retries + 1):
            try:
                stream = await asyncio.wait_for(
                    self.client.chat.completions.create(**kwargs),
                    timeout=self.config.connect_timeout
                )

                current_tool_calls = {}
                last_chunk_time = asyncio.get_event_loop().time()

                async for chunk in stream:
                    # 检查流式响应超时
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_chunk_time > 60:
                        yield StreamChunk(
                            type="error",
                            error="流式响应超时 - 60秒未收到数据"
                        )
                        return
                    last_chunk_time = current_time

                    delta = chunk.choices[0].delta if chunk.choices else None

                    if delta is None:
                        continue

                    # 文本内容
                    if delta.content:
                        yield StreamChunk(type="text", content=delta.content)

                    # 工具调用
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            tc_id = tc.id or list(current_tool_calls.keys())[-1] if current_tool_calls else None

                            if tc.id:
                                current_tool_calls[tc.id] = {
                                    "id": tc.id,
                                    "name": tc.function.name if tc.function else "",
                                    "arguments": ""
                                }
                                yield StreamChunk(
                                    type="tool_call",
                                    tool_call_id=tc.id,
                                    tool_name=tc.function.name if tc.function else None
                                )

                            if tc.function and tc.function.arguments:
                                if tc_id and tc_id in current_tool_calls:
                                    current_tool_calls[tc_id]["arguments"] += tc.function.arguments
                                yield StreamChunk(
                                    type="tool_call_delta",
                                    tool_call_id=tc_id,
                                    tool_args_delta=tc.function.arguments
                                )

                    # 完成
                    if chunk.choices[0].finish_reason:
                        for tc_id, tc_data in current_tool_calls.items():
                            try:
                                import json
                                tc_data["arguments"] = json.loads(tc_data["arguments"])
                            except:
                                pass

                        # 统一 usage 字段，确保包含 input_tokens/output_tokens/total_tokens
                        usage = None
                        if chunk.usage:
                            raw = chunk.usage.model_dump()
                            usage = {
                                "input_tokens": raw.get("prompt_tokens", 0),
                                "output_tokens": raw.get("completion_tokens", 0),
                                "total_tokens": raw.get("total_tokens", 0),
                            }
                        yield StreamChunk(
                            type="finish",
                            finish_reason=chunk.choices[0].finish_reason,
                            usage=usage
                        )

                        return

            except asyncio.TimeoutError:
                last_error = f"连接超时 (>{self.config.connect_timeout}s)"
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (2 ** attempt)
                    yield StreamChunk(
                        type="error",
                        error=f"⏱️ {last_error} - 第 {attempt + 1} 次重试，等待 {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                    continue

            except asyncio.CancelledError:
                raise

            except Exception as e:
                last_error = str(e)
                error_lower = last_error.lower()

                retryable = any(keyword in error_lower for keyword in [
                    "timeout", "connection", "network", "rate", "429",
                    "500", "502", "503", "504", "overloaded"
                ])

                if retryable and attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (2 ** attempt)
                    if "rate" in error_lower or "429" in last_error:
                        delay = max(delay, 10.0)

                    yield StreamChunk(
                        type="error",
                        error=f"🔄 {type(e).__name__}: {last_error[:100]} - 第 {attempt + 1} 次重试，等待 {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    yield StreamChunk(
                        type="error",
                        error=f"❌ {type(e).__name__}: {last_error}"
                    )
                    yield StreamChunk(
                        type="finish",
                        finish_reason="error"
                    )
                    return

        yield StreamChunk(
            type="error",
            error=f"❌ 已重试 {self.config.max_retries} 次仍然失败: {last_error}"
        )
        yield StreamChunk(
            type="finish",
            finish_reason="error"
        )
