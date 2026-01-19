"""
LLM Provider 基类和数据类型
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional


@dataclass
class StreamChunk:
    """流式响应块"""
    type: str  # "text", "tool_call", "tool_call_delta", "finish", "error"
    content: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    tool_args_delta: Optional[str] = None
    finish_reason: Optional[str] = None
    usage: Optional[dict] = None
    error: Optional[str] = None  # 错误信息


@dataclass
class LLMResponse:
    """完整响应"""
    content: str
    tool_calls: list[dict]
    finish_reason: str
    usage: dict


@dataclass
class LLMConfig:
    """LLM 配置"""
    timeout: float = 120.0  # 总超时时间（秒）
    connect_timeout: float = 30.0  # 连接超时（秒）
    max_retries: int = 3  # 最大重试次数
    retry_delay: float = 1.0  # 初始重试延迟（秒）


# 默认配置
DEFAULT_LLM_CONFIG = LLMConfig()


class BaseLLMProvider(ABC):
    """LLM Provider 基类"""

    config: LLMConfig = field(default_factory=lambda: DEFAULT_LLM_CONFIG)

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = None,
    ) -> AsyncIterator[StreamChunk]:
        """流式调用 LLM"""
        pass
