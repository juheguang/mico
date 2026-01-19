"""
错误处理模块 - 定义错误类型和重试机制
"""

from __future__ import annotations
import asyncio
import time
from typing import Callable, TypeVar, Any
from rich.console import Console
from rich.prompt import Prompt

console = Console()

T = TypeVar("T")


# ============ 错误类型 ============

class AgentError(Exception):
    """Agent 基础错误"""
    pass


class LLMError(AgentError):
    """LLM 相关错误"""
    pass


class LLMTimeoutError(LLMError):
    """LLM 调用超时"""
    pass


class LLMNetworkError(LLMError):
    """LLM 网络错误（可重试）"""
    pass


class LLMRateLimitError(LLMError):
    """LLM 速率限制"""
    def __init__(self, message: str, retry_after: float = None):
        super().__init__(message)
        self.retry_after = retry_after


class LLMAPIError(LLMError):
    """LLM API 错误"""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class ToolError(AgentError):
    """工具执行错误"""
    pass


class ToolTimeoutError(ToolError):
    """工具执行超时"""
    pass


# ============ 重试配置 ============

class RetryConfig:
    """重试配置"""
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_exceptions: tuple = None
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions or (
            LLMNetworkError,
            LLMTimeoutError,
            LLMRateLimitError,
            ConnectionError,
            TimeoutError,
        )


# 默认重试配置
DEFAULT_RETRY_CONFIG = RetryConfig()


# ============ 重试装饰器 ============

async def retry_async(
    func: Callable,
    config: RetryConfig = None,
    on_retry: Callable[[int, Exception, float], None] = None
) -> Any:
    """
    异步重试装饰器
    
    Args:
        func: 要执行的异步函数（无参数）
        config: 重试配置
        on_retry: 重试时的回调函数 (attempt, exception, delay)
    """
    config = config or DEFAULT_RETRY_CONFIG
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await func()
        except config.retryable_exceptions as e:
            last_exception = e
            
            if attempt >= config.max_retries:
                break
            
            # 计算延迟时间
            if isinstance(e, LLMRateLimitError) and e.retry_after:
                delay = e.retry_after
            else:
                delay = min(
                    config.initial_delay * (config.exponential_base ** attempt),
                    config.max_delay
                )
            
            # 回调
            if on_retry:
                on_retry(attempt + 1, e, delay)
            
            await asyncio.sleep(delay)
    
    raise last_exception


# ============ 错误处理交互 ============

class ErrorHandler:
    """错误处理器 - 提供用户交互"""
    
    @staticmethod
    def classify_exception(e: Exception) -> tuple[str, bool]:
        """
        分类异常
        
        Returns:
            (错误类型描述, 是否可重试)
        """
        error_name = type(e).__name__
        
        # 网络相关
        if "timeout" in str(e).lower() or isinstance(e, (asyncio.TimeoutError, TimeoutError)):
            return "⏱️ 超时", True
        
        if "connect" in str(e).lower() or "network" in str(e).lower():
            return "🌐 网络错误", True
        
        if isinstance(e, ConnectionError):
            return "🔌 连接失败", True
        
        # API 相关
        if "rate" in str(e).lower() or "429" in str(e):
            return "⚡ 速率限制", True
        
        if "401" in str(e) or "unauthorized" in str(e).lower():
            return "🔑 认证失败", False
        
        if "400" in str(e) or "invalid" in str(e).lower():
            return "❌ 请求无效", False
        
        if "500" in str(e) or "502" in str(e) or "503" in str(e):
            return "🔧 服务器错误", True
        
        # OpenAI 特定
        if "openai" in error_name.lower():
            if "APIConnectionError" in error_name:
                return "🌐 API 连接失败", True
            if "RateLimitError" in error_name:
                return "⚡ 速率限制", True
            if "APIStatusError" in error_name:
                return "❌ API 错误", False
        
        # Anthropic 特定
        if "anthropic" in error_name.lower():
            if "APIConnectionError" in error_name:
                return "🌐 API 连接失败", True
            if "RateLimitError" in error_name:
                return "⚡ 速率限制", True
        
        return f"❓ {error_name}", False
    
    @staticmethod
    def ask_user_action(error: Exception, context: str = "") -> str:
        """
        询问用户如何处理错误
        
        Returns:
            "retry" | "skip" | "abort"
        """
        error_type, retryable = ErrorHandler.classify_exception(error)
        
        console.print(f"\n[red]━━━━━━ 错误 ━━━━━━[/red]")
        console.print(f"[red]{error_type}[/red]")
        if context:
            console.print(f"[dim]位置: {context}[/dim]")
        console.print(f"[dim]详情: {str(error)[:200]}[/dim]")
        
        if retryable:
            choices = ["r", "s", "a"]
            choice_text = "[r]重试 / [s]跳过 / [a]中止"
        else:
            choices = ["s", "a"]
            choice_text = "[s]跳过 / [a]中止"
        
        response = Prompt.ask(
            f"\n如何处理? {choice_text}",
            choices=choices,
            default="r" if retryable else "s"
        )
        
        if response == "r":
            return "retry"
        elif response == "s":
            return "skip"
        else:
            return "abort"
    
    @staticmethod
    def format_retry_message(attempt: int, error: Exception, delay: float) -> str:
        """格式化重试消息"""
        error_type, _ = ErrorHandler.classify_exception(error)
        return f"[yellow]{error_type} - 第 {attempt} 次重试，等待 {delay:.1f}s...[/yellow]"


# ============ 超时工具 ============

async def with_timeout(coro, timeout: float, error_message: str = "操作超时"):
    """
    为协程添加超时
    
    Args:
        coro: 协程
        timeout: 超时时间（秒）
        error_message: 超时错误消息
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise LLMTimeoutError(f"{error_message} (>{timeout}s)")
