#!/usr/bin/env python3
"""
Mico - 主入口

一个简化版的 AI 编程助手，仿照 OpenCode 的核心架构实现。

使用方法:
    # 交互模式
    python main.py

    # 单次执行
    python main.py "帮我创建一个 hello world 程序"

    # 指定模型
    python main.py --model anthropic/claude-sonnet-4-20250514 "分析这个项目"
    python main.py --model deepseek/deepseek-chat "写一个排序算法"

    # 指定工作目录
    python main.py -d /path/to/project "分析这个项目"
    python main.py -d ../other-project "分析这个项目"

环境变量:
    OPENAI_API_KEY: OpenAI API Key
    ANTHROPIC_API_KEY: Anthropic API Key
    DEEPSEEK_API_KEY: DeepSeek API Key
    MICO_LOG_DIR: 日志目录 (默认: .mico/logs)
    MICO_USERNAME: 用户名 (用于欢迎界面显示)
"""

import asyncio
import os
import sys
from pathlib import Path

# 加载环境变量（明确从项目根目录读取 .env）
try:
    from dotenv import load_dotenv
    # 开发阶段固定使用绝对路径 .env
    env_path = Path("/Users/jiahao.zhu/Codebase/Cursor/chat001/mico/.env")
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path), override=True)
    else:
        load_dotenv(override=True)
except ImportError:
    pass

# 记录 dotenv 路径（用于启动时严格回显）
DOTENV_PATH = "/Users/jiahao.zhu/Codebase/Cursor/chat001/mico/.env"

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


def resolve_working_dir(directory: str) -> str:
    """
    解析工作目录，支持绝对路径和相对路径

    Args:
        directory: 用户输入的目录路径

    Returns:
        解析后的绝对路径
    """
    path = Path(directory).expanduser()

    # 如果是相对路径，基于当前工作目录解析
    if not path.is_absolute():
        path = Path.cwd() / path

    # 解析成规范路径（解析 .. 和 . 等）
    path = path.resolve()

    # 验证目录存在
    if not path.exists():
        console.print(f"[yellow]Warning: Directory does not exist: {path}[/yellow]")
        console.print(f"[dim]Creating directory...[/dim]")
        path.mkdir(parents=True, exist_ok=True)

    if not path.is_dir():
        console.print(f"[red]Error: Path is not a directory: {path}[/red]")
        sys.exit(1)

    return str(path)


def resolve_working_dir_relative(base_dir: str, directory: str) -> str:
    """
    基于指定的当前工作目录解析路径（用于 /cd）

    Args:
        base_dir: 当前工作目录
        directory: 用户输入的目录路径

    Returns:
        解析后的绝对路径
    """
    base_path = Path(base_dir)
    path = Path(directory).expanduser()

    # 如果是相对路径，基于当前工作目录解析
    if not path.is_absolute():
        path = base_path / path

    # 解析成规范路径（解析 .. 和 . 等）
    path = path.resolve()

    # 验证目录存在
    if not path.exists():
        console.print(f"[yellow]Warning: Directory does not exist: {path}[/yellow]")
        console.print(f"[dim]Creating directory...[/dim]")
        path.mkdir(parents=True, exist_ok=True)

    if not path.is_dir():
        console.print(f"[red]Error: Path is not a directory: {path}[/red]")
        sys.exit(1)

    return str(path)


def print_banner():
    """打印帮助信息"""
    from src.ui.startup import print_ascii_banner, print_gradient_text
    
    # 显示 ASCII Banner
    print_ascii_banner()
    
    # 显示渐变色标题
    print_gradient_text("Mico - Mini AI Coding Assistant")
    
    # 显示帮助信息
    help_text = """
Commands:
  /help        - Show this help
  /a           - Cycle agent (build/plan/explore)
  /model       - Switch model
  /cd <path>   - Change working directory
  /clear       - Clear conversation
  /sessions    - List all sessions
  /load <id>   - Load a previous session
  /delete <id> - Delete a session
  /info        - Show current session info
  /tokens      - Show token usage statistics
  /status      - Show status bar
  /quit        - Exit
"""
    console.print(help_text, style="dim")


async def interactive_mode(model: str, agent_name: str, working_dir: str, username: str = None):
    """交互式模式"""
    from src import (
        SessionManager, AgentManager,
        create_default_registry, create_default_permission_manager,
        parse_model, create_provider,
        AgentLoop,
    )
    from src.logger import get_logger, set_log_dir
    from src.ui.startup import (
        print_ascii_banner, print_gradient_text, print_welcome_message,
        print_status_bar, show_loading_step, print_token_stats
    )

    # 启动界面：ASCII Banner
    print_ascii_banner()
    
    # 渐变色欢迎文字
    print_welcome_message(username)
    
    # 显示加载步骤
    show_loading_step("Loading configuration...", "dots2", 0.3)
    
    # 设置日志目录（在工作目录下）
    log_dir = Path(working_dir) / ".mico" / "logs"
    set_log_dir(log_dir)
    logger = get_logger()
    
    show_loading_step("Setting up logger...", "dots3", 0.2)

    # 初始化组件
    show_loading_step("Initializing components...", "line", 0.2)
    session_manager = SessionManager()
    agent_manager = AgentManager(working_dir)
    tool_registry = create_default_registry()

    # 创建会话
    show_loading_step("Creating session...", "star", 0.2)
    session = session_manager.create(agent=agent_name, model=model)

    # 记录会话开始
    logger.session_start(
        session_id=session.id,
        agent=agent_name,
        model=model,
        working_dir=working_dir
    )
    
    # 显示状态栏
    console.print()
    print_status_bar(
        model=model,
        agent=agent_name,
        working_dir=working_dir,
        username=username
    )
    
    # 显示基本操作提示
    console.print()
    console.print("[bold cyan]💡 Quick Start:[/bold cyan]")
    console.print("[dim]  • Type your message to start a conversation[/dim]")
    console.print("[dim]  • Use /help to see all commands[/dim]")
    console.print("[dim]  • Use /tokens to view token usage statistics[/dim]")
    console.print("[dim]  • Use /status to show the status bar[/dim]")
    console.print("[dim]  • Use /cd <path> to change working directory[/dim]")
    console.print("[dim]  • Use /a to cycle agents[/dim]")
    console.print("[dim]  • Use /quit to exit[/dim]")
    console.print()

    while True:
        try:
            # 获取用户输入
            user_input = Prompt.ask("[bold green]You[/bold green]")

            if not user_input.strip():
                continue

            # 处理命令
            if user_input.startswith("/"):
                cmd = user_input.lower().strip()

                if cmd == "/quit" or cmd == "/exit":
                    console.print("[dim]Goodbye! 👋[/dim]")
                    break

                elif cmd == "/help":
                    print_banner()
                    continue

                elif cmd == "/clear":
                    session = session_manager.create(agent=agent_name, model=model)
                    console.print("[dim]Conversation cleared.[/dim]")
                    continue

                elif cmd == "/a":
                    available = [a.name for a in agent_manager.list()]
                    # 循环切换
                    if agent_name in available:
                        idx = available.index(agent_name)
                        agent_name = available[(idx + 1) % len(available)]
                    else:
                        agent_name = available[0] if available else agent_name

                    session.agent = agent_name
                    console.print(f"[dim]Switched to agent: {agent_name}[/dim]")
                    print_status_bar(
                        model=model,
                        agent=agent_name,
                        working_dir=working_dir,
                        username=username
                    )
                    continue

                elif cmd.startswith("/model"):
                    parts = cmd.split()
                    if len(parts) > 1:
                        model = parts[1]
                        session.model = model
                        console.print(f"[dim]Switched to model: {model}[/dim]")
                    else:
                        console.print(f"[dim]Current model: {model}[/dim]")
                    continue

                elif cmd.startswith("/cd"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) < 2:
                        console.print("[red]Usage: /cd <path>[/red]")
                        continue
                    new_dir = resolve_working_dir_relative(working_dir, parts[1].strip())
                    working_dir = new_dir
                    # 重新初始化依赖工作目录的管理器
                    agent_manager = AgentManager(working_dir)
                    console.print(f"[green]✓ Working directory set to: {working_dir}[/green]")
                    print_status_bar(
                        model=model,
                        agent=agent_name,
                        working_dir=working_dir,
                        username=username
                    )
                    continue

                elif cmd == "/sessions":
                    # 列出所有会话
                    sessions = session_manager.list_sessions()
                    if not sessions:
                        console.print("[dim]No sessions found.[/dim]")
                    else:
                        from rich.table import Table
                        table = Table(title="Sessions", show_header=True)
                        table.add_column("ID", style="cyan")
                        table.add_column("Title", style="white")
                        table.add_column("Agent", style="blue")
                        table.add_column("Messages", style="green")
                        table.add_column("Updated", style="dim")

                        for s in sessions[:20]:  # 只显示最近 20 个
                            # 高亮当前会话
                            is_current = "→ " if s.id == session.id else ""
                            table.add_row(
                                is_current + s.id,  # 5 位短 ID
                                s.title[:30] + "..." if len(s.title) > 30 else s.title,
                                s.agent,
                                str(len(s.messages)),
                                s.updated_at.strftime("%m-%d %H:%M")
                            )

                        console.print(table)
                        console.print(f"[dim]Use /load <id> to load a session (can use partial ID)[/dim]")
                    continue

                elif cmd.startswith("/load"):
                    # 加载会话
                    parts = user_input.split(maxsplit=1)
                    if len(parts) < 2:
                        console.print("[red]Usage: /load <session_id>[/red]")
                        continue

                    session_id = parts[1].strip()
                    loaded = session_manager.get(session_id)
                    if loaded:
                        session = loaded
                        agent_name = session.agent
                        model = session.model
                        console.print(f"[green]✓ Loaded session: {session.id}[/green]")
                        console.print(f"[dim]  Title: {session.title}[/dim]")
                        console.print(f"[dim]  Messages: {len(session.messages)}[/dim]")
                        console.print(f"[dim]  Agent: {agent_name}, Model: {model}[/dim]")
                    else:
                        console.print(f"[red]Session not found: {session_id}[/red]")
                    continue

                elif cmd.startswith("/delete"):
                    # 删除会话
                    parts = user_input.split(maxsplit=1)
                    if len(parts) < 2:
                        console.print("[red]Usage: /delete <session_id>[/red]")
                        continue

                    session_id = parts[1].strip()
                    target = session_manager.get(session_id)
                    if target:
                        if target.id == session.id:
                            console.print("[yellow]Cannot delete current session. Use /clear to start fresh.[/yellow]")
                        else:
                            session_manager.delete(target.id)
                            console.print(f"[green]✓ Deleted session: {target.id}[/green]")
                    else:
                        console.print(f"[red]Session not found: {session_id}[/red]")
                    continue

                elif cmd == "/info":
                    # 显示当前会话信息
                    console.print(f"\n[bold]Current Session Info[/bold]")
                    console.print(f"[dim]  ID:       {session.id}[/dim]")
                    console.print(f"[dim]  Title:    {session.title}[/dim]")
                    console.print(f"[dim]  Agent:    {session.agent}[/dim]")
                    console.print(f"[dim]  Model:    {session.model}[/dim]")
                    console.print(f"[dim]  Messages: {len(session.messages)}[/dim]")
                    console.print(f"[dim]  Created:  {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
                    console.print(f"[dim]  Updated:  {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
                    console.print()
                    continue

                elif cmd == "/tokens":
                    # 显示 Token 统计
                    from src.ui.startup import print_token_stats
                    # 收集所有消息的 token 统计
                    total_input = 0
                    total_output = 0
                    total_total = 0
                    
                    for msg in session.messages:
                        if hasattr(msg, 'tokens') and msg.tokens:
                            total_input += msg.tokens.get("input", 0)
                            total_output += msg.tokens.get("output", 0)
                            total_total += msg.tokens.get("total", 0)
                    
                    if total_total > 0:
                        tokens = {
                            "input": total_input,
                            "output": total_output,
                            "total": total_total
                        }
                        print_token_stats(tokens, show_bars=True)
                    else:
                        console.print("[dim]No token usage data available yet.[/dim]")
                    continue

                elif cmd == "/status":
                    print_status_bar(
                        model=model,
                        agent=agent_name,
                        working_dir=working_dir,
                        username=username
                    )
                    continue

                else:
                    console.print(f"[red]Unknown command: {cmd}[/red]")
                    console.print("[dim]Type /help for available commands[/dim]")
                    continue

            # 运行 Agent
            agent_config = agent_manager.get(agent_name) or agent_manager.default_agent()
            permission_manager = create_default_permission_manager()
            permission_manager.merge_rules(agent_config.permissions)

            provider_id, model_id = parse_model(model)
            provider = create_provider(provider_id, model_id)

            loop = AgentLoop(
                session=session,
                agent=agent_config,
                provider=provider,
                tool_registry=tool_registry,
                permission_manager=permission_manager,
                working_dir=working_dir
            )

            await loop.run(user_input)

            # 保存会话
            session_manager.save(session)

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted. Type /quit to exit.[/dim]")
            # 保存会话
            session_manager.save(session)
            continue

        except asyncio.CancelledError:
            console.print("\n[dim]Interrupted. Type /quit to exit.[/dim]")
            # 保存会话
            session_manager.save(session)
            continue

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            import traceback
            traceback.print_exc()
            continue


async def single_run(prompt: str, model: str, agent_name: str, working_dir: str):
    """单次执行模式"""
    from src import run_agent
    from src.logger import get_logger, set_log_dir

    # 设置日志目录
    log_dir = Path(working_dir) / ".mico" / "logs"
    set_log_dir(log_dir)
    logger = get_logger()

    try:
        result = await run_agent(
            prompt=prompt,
            model=model,
            agent_name=agent_name,
            working_dir=working_dir
        )

        # 输出最终结果
        for part in result.parts:
            if hasattr(part, "text") and part.text:
                console.print(Markdown(part.text))

    except Exception as e:
        logger.error(f"Single run failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def main():
    """主函数"""
    import argparse
    from src import list_providers

    parser = argparse.ArgumentParser(
        description="Mico - A Simple AI Coding Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        help="Prompt for single execution mode"
    )

    parser.add_argument(
        "-m", "--model",
        default=os.getenv("MICO_MODEL", "openai/gpt-4o"),
        help="Model to use (format: provider/model). Supported providers: openai, anthropic, deepseek"
    )

    parser.add_argument(
        "-a", "--agent",
        default=os.getenv("MICO_DEFAULT_AGENT", "build"),
        choices=["build", "plan"],
        help="Agent to use (env: MICO_DEFAULT_AGENT)"
    )

    parser.add_argument(
        "-d", "--directory",
        default=os.getenv("MICO_WORKING_DIR", "."),
        help="Working directory (absolute or relative path, env: MICO_WORKING_DIR)"
    )
    
    parser.add_argument(
        "-u", "--username",
        default=os.getenv("MICO_USERNAME", None),
        help="Username for welcome message (env: MICO_USERNAME)"
    )

    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List supported providers and models"
    )

    args = parser.parse_args()

    # 严格回显配置来源（方便定位为何状态栏未使用 .env）
    console.print("[dim]── Config (env → args) ──[/dim]")
    console.print(f"[dim].env path: {DOTENV_PATH} (exists: {Path(DOTENV_PATH).exists()})[/dim]")
    console.print(f"[dim]ENV  MICO_MODEL={os.getenv('MICO_MODEL')}[/dim]")
    console.print(f"[dim]ENV  MICO_DEFAULT_AGENT={os.getenv('MICO_DEFAULT_AGENT')}[/dim]")
    console.print(f"[dim]ENV  MICO_WORKING_DIR={os.getenv('MICO_WORKING_DIR')}[/dim]")
    console.print(f"[dim]ENV  MICO_USERNAME={os.getenv('MICO_USERNAME')}[/dim]")
    console.print(f"[dim]ARGS model={args.model} agent={args.agent} directory={args.directory} username={args.username}[/dim]")
    console.print("[dim]────────────────────────[/dim]")

    # 列出支持的 provider
    if args.list_providers:
        providers = list_providers()
        console.print("\n[bold]Supported Providers and Models:[/bold]\n")
        for provider_id, info in providers.items():
            env_key = info["env_key"]
            has_key = "✓" if os.getenv(env_key) else "✗"
            console.print(f"[cyan]{provider_id}[/cyan] (env: {env_key} [{has_key}])")
            for model in info["models"]:
                console.print(f"  - {model}")
            console.print()
        sys.exit(0)

    # 解析工作目录（支持绝对路径和相对路径）
    working_dir = resolve_working_dir(args.directory)

    # 检测可用的 API Key 并验证模型
    from src.llm import parse_model
    
    # 构建可用 provider 列表
    provider_keys = {
        "openai": ("OPENAI_API_KEY", "openai/gpt-4o"),
        "anthropic": ("ANTHROPIC_API_KEY", "anthropic/claude-sonnet-4-20250514"),
        "deepseek": ("DEEPSEEK_API_KEY", "deepseek/deepseek-chat"),
    }
    
    available_providers = [
        (provider_id, model) 
        for provider_id, (env_key, model) in provider_keys.items()
        if os.getenv(env_key)
    ]
    
    # 解析当前模型的 provider
    try:
        provider_id, _ = parse_model(args.model)
    except Exception:
        provider_id = args.model.split("/")[0].lower() if "/" in args.model else args.model.lower()
    
    # 检查模型是否有对应的 API Key
    env_key = provider_keys.get(provider_id, (None, None))[0]
    has_key = env_key and os.getenv(env_key) is not None
    
    # 如果没有对应的 Key，尝试自动选择或报错
    if not has_key:
        if available_providers:
            # 如果默认模型没有 Key，自动选择第一个可用的
            if args.model == os.getenv("MICO_MODEL", "openai/gpt-4o"):
                args.model = available_providers[0][1]
                console.print(f"[dim]Auto-selected model: {args.model} (based on available API keys)[/dim]")
            else:
                # 用户指定的模型没有 Key，报错
                console.print(f"[red]Error: No API key for model '{args.model}'[/red]")
                console.print(f"[dim]Available models with API keys:[/dim]")
                for _, model_name in available_providers:
                    console.print(f"[dim]  - {model_name}[/dim]")
                console.print(f"[dim]Use --model to specify one of the above, or set the corresponding API key[/dim]")
                sys.exit(1)
        else:
            console.print("[red]Error: No API keys found[/red]")
            console.print("[dim]Please set at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, or DEEPSEEK_API_KEY[/dim]")
            console.print("[dim]You can set them via environment variables or add them to your .env file[/dim]")
            sys.exit(1)

    # 运行
    try:
        if args.prompt:
            # 单次执行模式
            asyncio.run(single_run(
                prompt=args.prompt,
                model=args.model,
                agent_name=args.agent,
                working_dir=working_dir
            ))
        else:
            # 交互模式
            asyncio.run(interactive_mode(
                model=args.model,
                agent_name=args.agent,
                working_dir=working_dir,
                username=args.username
            ))
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye! 👋[/dim]")
        sys.exit(0)


if __name__ == "__main__":
    main()
