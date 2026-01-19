"""
消息格式化模块 - 使用 Panel 美化用户和 AI 消息显示
"""

from datetime import datetime
from rich.panel import Panel
from rich.markdown import Markdown
from rich.box import ROUNDED
from rich.text import Text

from .console import console


def format_user_message(text: str, show_timestamp: bool = True) -> Panel:
    """
    格式化用户消息为 Panel
    
    Args:
        text: 用户输入的文本
        show_timestamp: 是否显示时间戳
        
    Returns:
        Panel 组件
    """
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    title = "[bold green]👤 You[/bold green]"
    if show_timestamp:
        title += f" [dim]({timestamp})[/dim]"
    
    return Panel(
        text,
        title=title,
        border_style="green",
        box=ROUNDED
    )


def format_assistant_message(text: str, streaming: bool = False, show_timestamp: bool = True) -> Panel:
    """
    格式化 AI 助手消息为 Panel
    
    Args:
        text: AI 响应的文本
        streaming: 是否正在流式输出（用于显示光标）
        show_timestamp: 是否显示时间戳
        
    Returns:
        Panel 组件
    """
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    title = "[bold cyan]🤖 Assistant[/bold cyan]"
    if show_timestamp:
        title += f" [dim]({timestamp})[/dim]"
    
    # 如果文本为空，显示占位符
    if not text.strip():
        content = Text("[dim]思考中...[/dim]")
    else:
        # 尝试解析 Markdown
        try:
            content = Markdown(text)
        except Exception:
            # 如果 Markdown 解析失败，使用纯文本
            content = text
    
    # 流式输出时添加光标
    if streaming:
        if isinstance(content, Markdown):
            # Markdown 对象不能直接追加，转换为 Text
            content = Text(text) + Text("▌", style="blink cyan")
        else:
            content = Text(content) + Text("▌", style="blink cyan")
    
    return Panel(
        content,
        title=title,
        border_style="cyan",
        box=ROUNDED
    )


def format_system_message(text: str) -> Panel:
    """
    格式化系统消息为 Panel
    
    Args:
        text: 系统消息文本
        
    Returns:
        Panel 组件
    """
    return Panel(
        Markdown(text) if text.strip() else Text("[dim]系统消息[/dim]"),
        title="[bold yellow]⚙️  System[/bold yellow]",
        border_style="yellow",
        box=ROUNDED
    )


def print_user_message(text: str):
    """打印用户消息"""
    console.print()
    console.print(format_user_message(text))
    console.print()


def print_assistant_message(text: str, streaming: bool = False):
    """打印 AI 助手消息"""
    console.print()
    console.print(format_assistant_message(text, streaming=streaming))
    console.print()


def print_system_message(text: str):
    """打印系统消息"""
    console.print()
    console.print(format_system_message(text))
    console.print()
