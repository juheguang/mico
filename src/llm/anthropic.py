"""
Anthropic Claude Provider - 带超时和重试机制
"""

from __future__ import annotations
import os
import asyncio
from typing import AsyncIterator

from .base import BaseLLMProvider, StreamChunk, LLMConfig, DEFAULT_LLM_CONFIG


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude Provider"""

    def __init__(
        self,
        api_key: str = None,
        model: str = "claude-sonnet-4-20250514",
        config: LLMConfig = None
    ):
        from anthropic import AsyncAnthropic

        self.model = model
        self.config = config or DEFAULT_LLM_CONFIG
        self.client = AsyncAnthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            timeout=self.config.timeout,
            max_retries=0
        )

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """转换 OpenAI 格式工具到 Anthropic 格式"""
        result = []
        for tool in tools:
            if tool["type"] == "function":
                result.append({
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "input_schema": tool["function"]["parameters"]
                })
        return result

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = None,
    ) -> AsyncIterator[StreamChunk]:
        # 分离 system 消息
        system = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        timeout = timeout or self.config.timeout
        last_error = None

        # 重试循环
        for attempt in range(self.config.max_retries + 1):
            try:
                async with self.client.messages.stream(**kwargs) as stream:
                    current_tool_id = None
                    current_tool_name = None
                    current_tool_args = ""
                    last_event_time = asyncio.get_event_loop().time()

                    async for event in stream:
                        # 检查流式响应超时
                        current_time = asyncio.get_event_loop().time()
                        if current_time - last_event_time > 60:
                            yield StreamChunk(
                                type="error",
                                error="流式响应超时 - 60秒未收到数据"
                            )
                            return
                        last_event_time = current_time

                        if event.type == "content_block_start":
                            if event.content_block.type == "tool_use":
                                current_tool_id = event.content_block.id
                                current_tool_name = event.content_block.name
                                current_tool_args = ""
                                yield StreamChunk(
                                    type="tool_call",
                                    tool_call_id=current_tool_id,
                                    tool_name=current_tool_name
                                )

                        elif event.type == "content_block_delta":
                            if event.delta.type == "text_delta":
                                yield StreamChunk(type="text", content=event.delta.text)
                            elif event.delta.type == "input_json_delta":
                                current_tool_args += event.delta.partial_json
                                yield StreamChunk(
                                    type="tool_call_delta",
                                    tool_call_id=current_tool_id,
                                    tool_args_delta=event.delta.partial_json
                                )

                        elif event.type == "message_stop":
                            message = await stream.get_final_message()
                            finish_reason = message.stop_reason
                            if finish_reason == "end_turn":
                                finish_reason = "stop"
                            elif finish_reason == "tool_use":
                                finish_reason = "tool_calls"

                            usage = {
                                "input_tokens": message.usage.input_tokens,
                                "output_tokens": message.usage.output_tokens,
                                "total_tokens": message.usage.input_tokens + message.usage.output_tokens
                            }
                            yield StreamChunk(
                                type="finish",
                                finish_reason=finish_reason,
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
