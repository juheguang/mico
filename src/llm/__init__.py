"""
LLM 模块 - 提供各种 LLM Provider 的封装
"""

from .base import BaseLLMProvider, StreamChunk, LLMResponse, LLMConfig, DEFAULT_LLM_CONFIG
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .deepseek import DeepSeekProvider

# 支持的 Provider 列表
SUPPORTED_PROVIDERS = {
    "openai": {
        "class": OpenAIProvider,
        "env_key": "OPENAI_API_KEY",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "o1", "o1-mini"]
    },
    "anthropic": {
        "class": AnthropicProvider,
        "env_key": "ANTHROPIC_API_KEY",
        "models": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]
    },
    "deepseek": {
        "class": DeepSeekProvider,
        "env_key": "DEEPSEEK_API_KEY",
        "models": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner (无工具调用)"]
    },
    "openai-compatible": {
        "class": OpenAIProvider,
        "env_key": "OPENAI_API_KEY",
        "models": []
    }
}


def create_provider(provider_id: str, model_id: str, **kwargs) -> BaseLLMProvider:
    """创建 Provider 实例"""
    if provider_id == "openai":
        return OpenAIProvider(model=model_id, **kwargs)
    elif provider_id == "anthropic":
        return AnthropicProvider(model=model_id, **kwargs)
    elif provider_id == "deepseek":
        return DeepSeekProvider(model=model_id, **kwargs)
    elif provider_id == "openai-compatible":
        return OpenAIProvider(model=model_id, **kwargs)
    else:
        raise ValueError(
            f"Unknown provider: {provider_id}\n"
            f"Supported providers: {list(SUPPORTED_PROVIDERS.keys())}"
        )


def parse_model(model_str: str) -> tuple[str, str]:
    """解析 provider/model 格式"""
    if "/" in model_str:
        parts = model_str.split("/", 1)
        return parts[0], parts[1]
    # 默认使用 OpenAI
    return "openai", model_str


def list_providers() -> dict:
    """列出所有支持的 Provider"""
    return SUPPORTED_PROVIDERS


__all__ = [
    "BaseLLMProvider",
    "StreamChunk",
    "LLMResponse",
    "LLMConfig",
    "DEFAULT_LLM_CONFIG",
    "OpenAIProvider",
    "AnthropicProvider",
    "DeepSeekProvider",
    "create_provider",
    "parse_model",
    "list_providers",
    "SUPPORTED_PROVIDERS",
]
