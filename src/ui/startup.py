"""
启动界面模块 - ASCII Banner、渐变色、状态栏、加载动画
"""

from datetime import datetime
from rich.console import Console
from rich.text import Text
from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.spinner import Spinner
from rich.box import MINIMAL, ROUNDED

from .console import console


def print_ascii_banner():
    """打印 Mico ASCII 艺术 Banner"""
    # 明确区分 C 与 O：C 右侧开口，O 完全闭合
    art = """
    ███╗   ███╗  ██╗   █████╗    █████╗
    ████╗ ████║  ██║  ██╔══╝   ██╔══██╗
    ██╔████╔██║  ██║  ██║      ██║  ██║
    ██║╚██╔╝██║  ██║  ██║      ██║  ██║
    ██║ ╚═╝ ██║  ██║  ╚█████╗  ╚█████╔╝
    ╚═╝     ╚═╝  ╚═╝   ╚════╝   ╚════╝
    """
    
    # 渐变色 ASCII Art（从青色渐变到紫色）
    lines = art.strip().split('\n')
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        ratio = i / len(lines)
        if ratio < 0.5:
            color = "cyan"
        else:
            color = "magenta"
        console.print(Align.center(line), style=f"bold {color}")
    console.print()


def print_gradient_text(text: str, colors: list[str] = None):
    """
    打印渐变色文字
    
    Args:
        text: 要显示的文字
        colors: 颜色列表，默认使用蓝紫渐变
    """
    if colors is None:
        colors = ["deep_sky_blue1", "dodger_blue1", "blue", "blue_violet", "medium_purple", "magenta"]
    
    gradient_text = Text()
    for i, char in enumerate(text):
        color_idx = int(i / len(text) * len(colors))
        color = colors[min(color_idx, len(colors) - 1)]
        gradient_text.append(char, style=f"bold {color}")
    
    console.print(Align.center(gradient_text))
    console.print()


def print_status_bar(
    model: str = "unknown",
    agent: str = "unknown",
    working_dir: str = ".",
    username: str = None,
    tokens: dict = None
):
    """
    打印状态栏
    
    Args:
        model: 当前使用的模型
        agent: 当前使用的 Agent
        working_dir: 工作目录
        username: 用户名
        tokens: Token 统计信息
    """
    status_items = []
    
    if username:
        status_items.append(f"[bold cyan]👤 {username}[/bold cyan]")
    
    status_items.append(f"[bold yellow]🤖 {model}[/bold yellow]")
    # 显示完整路径，便于确认当前工作目录
    status_items.append(f"[bold green]📁 {working_dir}[/bold green]")
    status_items.append(f"[bold blue]🔧 {agent}[/bold blue]")
    
    if tokens:
        input_tokens = tokens.get("input", 0)
        output_tokens = tokens.get("output", 0)
        total_tokens = tokens.get("total", 0)
        status_items.append(f"[dim]Tokens: {total_tokens:,} (in: {input_tokens:,}, out: {output_tokens:,})[/dim]")
    
    status_bar = " │ ".join(status_items)
    console.print(Panel(status_bar, box=MINIMAL, style="on grey23"))
    console.print()


def print_welcome_message(username: str = None):
    """
    打印欢迎消息
    
    Args:
        username: 用户名
    """
    # 固定欢迎语，不显示 welcome back
    print_gradient_text("Mico - Mini AI Coding Assistant")
    console.print()


def show_loading_step(description: str, spinner_name: str = "dots", duration: float = 0.3):
    """
    显示加载步骤（使用 console.status）
    
    Args:
        description: 步骤描述
        spinner_name: Spinner 类型
        duration: 显示时长（秒）
    """
    import time
    with console.status(f"[bold cyan]{description}[/bold cyan]", spinner=spinner_name):
        time.sleep(duration)


def show_progress_steps(steps: list[tuple[str, str]]):
    """
    显示多个加载步骤（使用 Progress）
    
    Args:
        steps: 步骤列表，每个元素为 (description, spinner_name)
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        console=console
    ) as progress:
        tasks = []
        for desc, spinner_name in steps:
            task = progress.add_task(desc, total=None)
            tasks.append((task, spinner_name))
        
        # 模拟进度（实际使用时应该根据真实操作完成情况更新）
        import time
        for task, spinner_name in tasks:
            time.sleep(0.5)  # 模拟操作时间
            progress.update(task, advance=100)


def print_token_stats(tokens: dict, show_bars: bool = True):
    """
    打印 Token 统计信息
    
    Args:
        tokens: Token 统计字典，包含 input, output, total
        show_bars: 是否显示进度条
    """
    input_tokens = tokens.get("input", 0)
    output_tokens = tokens.get("output", 0)
    total_tokens = tokens.get("total", 0)
    
    # 假设最大 token 限制（可以根据实际模型调整）
    max_tokens = 128000  # 例如 GPT-4o 的上下文窗口
    
    table = Table(box=ROUNDED, show_header=False, padding=(0, 2))
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")
    
    if show_bars:
        table.add_column("Bar", width=30)
        
        # Input tokens bar
        input_ratio = min(input_tokens / max_tokens, 1.0)
        input_bar_length = int(input_ratio * 30)
        input_bar = "█" * input_bar_length + "░" * (30 - input_bar_length)
        table.add_row("Input", f"{input_tokens:,}", f"[cyan]{input_bar}[/cyan]")
        
        # Output tokens bar
        output_ratio = min(output_tokens / max_tokens, 1.0)
        output_bar_length = int(output_ratio * 30)
        output_bar = "█" * output_bar_length + "░" * (30 - output_bar_length)
        table.add_row("Output", f"{output_tokens:,}", f"[green]{output_bar}[/green]")
        
        # Total tokens bar
        total_ratio = min(total_tokens / max_tokens, 1.0)
        total_bar_length = int(total_ratio * 30)
        total_bar = "█" * total_bar_length + "░" * (30 - total_bar_length)
        table.add_row("Total", f"{total_tokens:,} / {max_tokens:,}", f"[yellow]{total_bar}[/yellow]")
    else:
        table.add_row("Input", f"{input_tokens:,}")
        table.add_row("Output", f"{output_tokens:,}")
        table.add_row("Total", f"{total_tokens:,}")
    
    panel = Panel(table, title="[bold]📊 Token Usage[/bold]", border_style="cyan", box=ROUNDED)
    console.print()
    console.print(panel)
    console.print()


from pathlib import Path
