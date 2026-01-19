"""
主循环 - Agent 的核心执行流程
"""

from __future__ import annotations
import json
import asyncio
import time
from datetime import datetime
from typing import TYPE_CHECKING

from .models import (
    Session, UserMessage, AssistantMessage,
    TextPart, ToolPart, ToolCall, ToolState,
    AgentConfig
)
from .tools import ToolRegistry, ToolContext, ToolResult
from .permission import PermissionManager, PermissionDeniedError, PermissionRejectedError
from .llm import BaseLLMProvider, StreamChunk, parse_model, create_provider
from .session import (
    create_user_message, create_assistant_message,
    add_text_part, add_tool_part, update_tool_part,
    messages_to_openai_format
)
from .logger import get_logger
from .ui import (
    console, EditStreamPreview,
    print_user_message, format_assistant_message,
    format_code_with_syntax, format_list_output_simple, format_diff
)


# Doom loop 检测阈值
DOOM_LOOP_THRESHOLD = 3


class AgentLoop:
    """
    Agent 主循环

    核心流程：
    1. 用户输入 → 创建 UserMessage
    2. 进入循环：
       a. 调用 LLM (stream)
       b. 处理响应（文本/工具调用）
       c. 执行工具
       d. 检查终止条件（stop / tool_calls）
       e. 如果有工具调用，继续循环
    3. 返回最终响应
    """

    def __init__(
        self,
        session: Session,
        agent: AgentConfig,
        provider: BaseLLMProvider,
        tool_registry: ToolRegistry,
        permission_manager: PermissionManager,
        working_dir: str = "."
    ):
        self.session = session
        self.agent = agent
        self.provider = provider
        self.tools = tool_registry
        self.permission = permission_manager
        self.working_dir = working_dir
        self.aborted = False

    def abort(self):
        """中止当前循环"""
        self.aborted = True

    async def run(self, user_input: str) -> AssistantMessage:
        """
        运行主循环

        Args:
            user_input: 用户输入文本

        Returns:
            最终的助手消息
        """
        logger = get_logger()

        # 1. 创建用户消息
        user_msg = create_user_message(
            self.session,
            user_input,
            agent=self.agent.name,
            model=self.session.model
        )

        # 记录用户输入
        logger.user_input(
            session_id=self.session.id,
            message_id=user_msg.id,
            text=user_input
        )

        # 显示用户消息（带时间戳，不用 Panel）
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        console.print(f"\n[bold green]👤 You[/bold green] [dim]({timestamp})[/dim]")
        console.print(f"{user_input}\n")

        # 2. 主循环
        step = 0
        assistant_msg = None
        while step < self.agent.max_steps and not self.aborted:
            step += 1
            console.print(f"[dim]── Step {step} ──[/dim]")

            # 创建助手消息
            assistant_msg = create_assistant_message(
                self.session,
                parent_id=user_msg.id,
                agent=self.agent.name,
                model=self.session.model
            )

            try:
                # 处理一轮 LLM 响应
                finish_reason = await self._process_stream(assistant_msg)

                assistant_msg.finish_reason = finish_reason
                assistant_msg.completed_at = datetime.now()

                # 检查终止条件
                if finish_reason != "tool_calls":
                    console.print(f"\n[green]✓ Completed (reason: {finish_reason})[/green]\n")
                    return assistant_msg

                # 有工具调用，检查 doom loop
                if self._detect_doom_loop():
                    console.print("[yellow]⚠ Doom loop detected![/yellow]")
                    try:
                        await self.permission.check("doom_loop", ["*"])
                    except PermissionRejectedError:
                        assistant_msg.finish_reason = "stopped"
                        return assistant_msg

            except asyncio.CancelledError:
                # 用户按 Ctrl+C 中断
                assistant_msg.finish_reason = "interrupted"
                assistant_msg.completed_at = datetime.now()
                return assistant_msg

            except PermissionDeniedError as e:
                console.print(f"[red]✗ Permission denied: {e}[/red]")
                assistant_msg.error = str(e)
                assistant_msg.finish_reason = "error"
                return assistant_msg

            except PermissionRejectedError as e:
                console.print(f"[yellow]✗ User rejected: {e}[/yellow]")
                assistant_msg.finish_reason = "stopped"
                return assistant_msg

            except Exception as e:
                console.print(f"[red]✗ Error: {e}[/red]")
                assistant_msg.error = str(e)
                assistant_msg.finish_reason = "error"
                return assistant_msg

        # 达到最大步数
        console.print(f"[yellow]⚠ Reached max steps ({self.agent.max_steps})[/yellow]")
        return assistant_msg

    async def _process_stream(self, assistant_msg: AssistantMessage) -> str:
        """
        处理 LLM 流式响应

        Returns:
            finish_reason
        """
        logger = get_logger()
        start_time = time.time()

        # 构建消息历史
        messages = self._build_messages()

        # 获取工具定义
        tools = self.tools.to_openai_tools()

        # 记录 LLM 请求
        provider_id, model_id = parse_model(self.session.model)
        logger.llm_request(
            session_id=self.session.id,
            provider=provider_id,
            model=model_id,
            messages_count=len(messages),
            tools_count=len(tools) if tools else 0
        )

        # 调用 LLM
        current_text = ""
        tool_calls: dict[str, ToolCall] = {}
        edit_previewers: dict[str, EditStreamPreview] = {}
        finish_reason = "stop"
        preparing_questions_status = None

        # 流式输出：先打印标题（带时间戳），然后直接输出内容
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        console.print()
        console.print(f"[bold cyan]🤖 Assistant[/bold cyan] [dim]({timestamp})[/dim]")
        console.print("[dim]─────────────────────────────────[/dim]")
        
        # 标记是否有文本输出（用于决定是否显示 Panel）
        has_text_output = False

        try:
            async for chunk in self.provider.stream(
                messages=messages,
                tools=tools,
                temperature=self.agent.temperature
            ):
                if self.aborted:
                    break

                if chunk.type == "text":
                    current_text += chunk.content
                    has_text_output = True
                    console.print(chunk.content, end="")

                elif chunk.type == "tool_call":
                    tool_calls[chunk.tool_call_id] = ToolCall(
                        id=chunk.tool_call_id,
                        tool_name=chunk.tool_name,
                        input={},
                        state=ToolState.PENDING
                    )
                    # ask_user: 显示准备问题的动态提示（直到 finish）
                    if chunk.tool_name == "ask_user" and preparing_questions_status is None:
                        from rich.status import Status
                        preparing_questions_status = Status(
                            "[cyan]Preparing questions...[/cyan]",
                            console=console,
                            spinner="dots"
                        )
                        preparing_questions_status.start()
                    # 如果是 edit 工具，初始化流式预览器
                    if chunk.tool_name == "edit":
                        edit_previewers[chunk.tool_call_id] = EditStreamPreview()
                        console.print(f"\n[blue]🔧 edit[/blue] [dim](生成中...)[/dim]")

                elif chunk.type == "tool_call_delta":
                    if chunk.tool_call_id in tool_calls:
                        tc = tool_calls[chunk.tool_call_id]
                        # 累积参数字符串
                        if not hasattr(tc, "_args_str"):
                            tc._args_str = ""
                        tc._args_str += chunk.tool_args_delta or ""

                        # 如果是 edit 工具，进行流式预览
                        if chunk.tool_call_id in edit_previewers:
                            previewer = edit_previewers[chunk.tool_call_id]
                            # 尝试提取 file_path
                            if previewer.file_path == "unknown" and '"file_path"' in tc._args_str:
                                try:
                                    import re
                                    match = re.search(r'"file_path"\s*:\s*"([^"]+)"', tc._args_str)
                                    if match:
                                        previewer.file_path = match.group(1)
                                except:
                                    pass
                            # 处理增量内容
                            previewer.process_delta(chunk.tool_args_delta)

                elif chunk.type == "error":
                    # 显示错误/重试消息
                    console.print(f"\n[yellow]{chunk.error}[/yellow]")

                elif chunk.type == "finish":
                    finish_reason = chunk.finish_reason
                    if chunk.usage:
                        assistant_msg.tokens = {
                            "input": chunk.usage.get("input_tokens", 0),
                            "output": chunk.usage.get("output_tokens", 0),
                            "total": chunk.usage.get("total_tokens", 0)
                        }
                    if preparing_questions_status is not None:
                        preparing_questions_status.stop()
                        preparing_questions_status = None
                    
                    # 流式输出完成
                    # 注意：流式输出时已经直接打印了内容，这里不再重复显示 Panel
                    # 保持流式输出的实时感，避免重复显示
                    
                    # 如果是错误完成，询问用户
                    if finish_reason == "error":
                        console.print()
                        from rich.prompt import Prompt
                        action = Prompt.ask(
                            "\n[yellow]LLM 调用失败，如何处理?[/yellow]",
                            choices=["r", "s", "a"],
                            default="r"
                        )
                        if action == "r":
                            # 重试：重新调用 _process_stream
                            console.print("[dim]重新尝试...[/dim]")
                            return await self._process_stream(assistant_msg)
                        elif action == "a":
                            # 中止
                            self.aborted = True
                            finish_reason = "aborted"
                        # s = 跳过，继续返回 error

        except asyncio.CancelledError:
            console.print("\n[yellow]⚠ Interrupted[/yellow]")
            finish_reason = "interrupted"
            self.aborted = True
            if current_text:
                add_text_part(assistant_msg, current_text)
            if preparing_questions_status is not None:
                preparing_questions_status.stop()
                preparing_questions_status = None
            raise

        # 记录 LLM 响应
        duration_ms = (time.time() - start_time) * 1000
        logger.llm_response(
            session_id=self.session.id,
            finish_reason=finish_reason,
            tokens=assistant_msg.tokens or {},
            duration_ms=duration_ms
        )

        console.print()  # 换行

        # 添加文本部分
        if current_text:
            add_text_part(assistant_msg, current_text)

        # 处理工具调用
        if tool_calls:
            for tc in tool_calls.values():
                # 解析参数
                if hasattr(tc, "_args_str"):
                    try:
                        tc.input = json.loads(tc._args_str)
                    except:
                        tc.input = {"raw": tc._args_str}
                    delattr(tc, "_args_str")

                # 添加到消息
                add_tool_part(assistant_msg, tc)

            # 执行工具
            await self._execute_tools(assistant_msg, tool_calls)

            # 如果有工具调用，finish_reason 应该是 tool_calls
            if finish_reason == "stop":
                finish_reason = "tool_calls"

        return finish_reason

    async def _execute_tools(
        self,
        assistant_msg: AssistantMessage,
        tool_calls: dict[str, ToolCall]
    ):
        """执行工具调用"""
        logger = get_logger()
        from rich.status import Status

        for call_id, tc in tool_calls.items():
            tool = self.tools.get(tc.tool_name)
            if not tool:
                update_tool_part(
                    assistant_msg, call_id,
                    ToolState.ERROR,
                    error=f"Unknown tool: {tc.tool_name}"
                )
                logger.tool_error(
                    session_id=self.session.id,
                    call_id=call_id,
                    tool_name=tc.tool_name,
                    error=f"Unknown tool: {tc.tool_name}"
                )
                continue

            # 构建工具调用摘要
            tool_summary = self._format_tool_summary(tc)

            # 显示工具调用开始
            if tc.tool_name != "edit":
                console.print(f"\n[blue]🔧 {tc.tool_name}[/blue]")
                console.print(f"[dim]   {tool_summary}[/dim]")
            else:
                console.print(f"[dim]   执行写入操作...[/dim]")

            # 记录工具调用
            logger.tool_call(
                session_id=self.session.id,
                call_id=call_id,
                tool_name=tc.tool_name,
                input_data=tc.input
            )

            # 更新状态为运行中
            update_tool_part(assistant_msg, call_id, ToolState.RUNNING)

            # 创建执行上下文
            ctx = ToolContext(
                session_id=self.session.id,
                message_id=assistant_msg.id,
                agent=self.agent.name,
                permission_manager=self.permission,
                working_dir=self.working_dir
            )

            tool_start_time = time.time()

            try:
                # 预先处理可能的权限询问，避免被执行中状态覆盖输入提示
                precheck_patterns: list[str] = []
                if tc.tool_name == "bash":
                    command = tc.input.get("command")
                    if command:
                        precheck_patterns = [command]
                elif tc.tool_name == "edit":
                    file_path = tc.input.get("file_path")
                    if file_path:
                        precheck_patterns = [file_path]
                elif tc.tool_name == "read":
                    file_path = tc.input.get("file_path")
                    if file_path:
                        precheck_patterns = [file_path]
                elif tc.tool_name == "list":
                    path = tc.input.get("path")
                    if path:
                        precheck_patterns = [path]
                elif tc.tool_name == "glob":
                    pattern = tc.input.get("pattern")
                    if pattern:
                        precheck_patterns = [pattern]

                if precheck_patterns:
                    await self.permission.check(tc.tool_name, precheck_patterns, tc.input)
                    ctx.preapprove(tc.tool_name, precheck_patterns)

                # ask_user 需要占用终端输入，避免 Status 刷新干扰
                if tc.tool_name == "ask_user":
                    result = await tool.execute(tc.input, ctx)
                else:
                    # 使用 Status 显示执行中的状态
                    with Status(
                        f"[cyan]执行中...[/cyan]",
                        console=console,
                        spinner="dots"
                    ) as status:
                        async def update_status():
                            elapsed = 0
                            while True:
                                await asyncio.sleep(0.5)
                                elapsed += 0.5
                            status.update(f"[cyan]执行中... ({elapsed:.1f}s)[/cyan]")

                    status_task = asyncio.create_task(update_status())

                    try:
                        result = await tool.execute(tc.input, ctx)
                    finally:
                        status_task.cancel()
                        try:
                            await status_task
                        except asyncio.CancelledError:
                            pass

                # 记录工具结果
                duration_ms = (time.time() - tool_start_time) * 1000
                logger.tool_result(
                    session_id=self.session.id,
                    call_id=call_id,
                    tool_name=tc.tool_name,
                    success=True,
                    output_length=len(result.output),
                    duration_ms=duration_ms
                )

                # 更新结果
                update_tool_part(
                    assistant_msg, call_id,
                    ToolState.COMPLETED,
                    output=result.output
                )

                # 显示结果摘要
                self._display_tool_result(tc, result, duration_ms)

            except (PermissionDeniedError, PermissionRejectedError) as e:
                duration_ms = (time.time() - tool_start_time) * 1000
                logger.tool_error(
                    session_id=self.session.id,
                    call_id=call_id,
                    tool_name=tc.tool_name,
                    error=f"Permission error: {e}"
                )
                update_tool_part(
                    assistant_msg, call_id,
                    ToolState.ERROR,
                    error=str(e)
                )
                console.print(f"[red]   ✗ 权限被拒绝: {e}[/red]")
                raise

            except Exception as e:
                duration_ms = (time.time() - tool_start_time) * 1000
                logger.tool_error(
                    session_id=self.session.id,
                    call_id=call_id,
                    tool_name=tc.tool_name,
                    error=str(e)
                )
                update_tool_part(
                    assistant_msg, call_id,
                    ToolState.ERROR,
                    error=str(e)
                )
                console.print(f"[red]   ✗ 错误: {e}[/red]")

    def _format_tool_summary(self, tc: ToolCall) -> str:
        """格式化工具调用摘要"""
        tool_name = tc.tool_name
        input_data = tc.input

        if tool_name == "edit":
            file_path = input_data.get("file_path", "unknown")
            old_string = input_data.get("old_string", "")
            new_string = input_data.get("new_string", "")
            lines = len(new_string.split("\n")) if new_string else 0

            if not old_string:
                return f"创建文件: {file_path} ({lines} 行)"
            else:
                return f"编辑文件: {file_path} ({lines} 行新内容)"

        elif tool_name == "read":
            file_path = input_data.get("file_path", "unknown")
            return f"读取文件: {file_path}"

        elif tool_name == "bash":
            command = input_data.get("command", "")
            if len(command) > 80:
                command = command[:77] + "..."
            return f"执行命令: {command}"

        elif tool_name == "glob":
            pattern = input_data.get("pattern", "*")
            return f"搜索文件: {pattern}"

        elif tool_name == "list":
            path = input_data.get("path", ".")
            return f"列出目录: {path}"

        elif tool_name == "ask_user":
            questions = input_data.get("questions", [])
            return f"向用户提问: {len(questions)} 个问题"

        else:
            summary = json.dumps(input_data, ensure_ascii=False)
            if len(summary) > 100:
                summary = summary[:97] + "..."
            return summary

    def _display_tool_result(self, tc: ToolCall, result: ToolResult, duration_ms: float):
        """显示工具执行结果（美化版）"""
        tool_name = tc.tool_name
        output = result.output
        input_data = tc.input

        # 格式化时间显示
        if duration_ms >= 1000:
            duration_str = f"[dim]({duration_ms/1000:.1f}s)[/dim]"
        else:
            duration_str = f"[dim]({duration_ms:.0f}ms)[/dim]"

        if tool_name == "edit":
            new_string = input_data.get("new_string", "")
            old_string = input_data.get("old_string", "")
            file_path = input_data.get("file_path", "unknown")
            lines_written = len(new_string.split("\n")) if new_string else 0
            chars_written = len(new_string)

            # edit 工具在流式预览中已经显示了最后5行，这里只显示完成信息
            # 不再打印整个文件，保持简洁
            if not old_string:
                console.print(f"[green]✓ 文件已创建: {file_path} ({lines_written} 行, {chars_written} 字符)[/green] {duration_str}")
            else:
                console.print(f"[green]✓ 文件已更新: {file_path} ({lines_written} 行, {chars_written} 字符)[/green] {duration_str}")

        elif tool_name == "read":
            file_path = input_data.get("file_path", "unknown")
            lines = len(output.split("\n"))
            chars = len(output)
            
            # read 工具不打印整个文件，只显示统计信息
            # 如果用户需要查看内容，可以要求 AI 使用 edit 工具或直接显示部分内容
            console.print(f"[green]✓ 已读取: {file_path} ({lines} 行, {chars} 字符)[/green] {duration_str}")

        elif tool_name == "bash":
            command = input_data.get("command", "unknown")
            output_lines = output.strip().split("\n") if output.strip() else []
            
            # 使用 Panel 美化显示
            from rich.panel import Panel
            from rich.box import ROUNDED
            
            if output_lines:
                # 有输出，显示结果
                if len(output_lines) <= 10:
                    # 输出较少，全部显示
                    output_text = "\n".join(output_lines)
                else:
                    # 输出较多，显示前5行和后5行
                    output_text = "\n".join(output_lines[:5])
                    output_text += f"\n[dim]... ({len(output_lines) - 10} 行已省略) ...[/dim]\n"
                    output_text += "\n".join(output_lines[-5:])
                
                panel = Panel(
                    output_text,
                    title=f"[bold blue]🔧 bash: {command}[/bold blue]",
                    border_style="blue",
                    box=ROUNDED
                )
                console.print()
                console.print(panel)
            else:
                # 无输出，只显示命令
                console.print(f"[blue]🔧 bash:[/blue] {command}")
            
            console.print(f"[green]✓ 命令完成[/green] {duration_str}")

        elif tool_name == "glob":
            files = output.strip().split("\n") if output.strip() else []
            console.print(f"[green]   ✓ 找到 {len(files)} 个文件[/green] {duration_str}")

        elif tool_name == "list":
            # 使用目录树显示
            if output.strip():
                console.print()
                tree = format_list_output_simple(output)
                console.print(tree)
                items = output.strip().split("\n")
                console.print(f"[green]✓ {len(items)} 个条目[/green] {duration_str}")
            else:
                console.print(f"[green]✓ 空目录[/green] {duration_str}")

        elif tool_name == "ask_user":
            # 输出问答结果摘要
            try:
                data = json.loads(output)
                summary = data.get("summary", "")
            except Exception:
                summary = output
            if summary:
                console.print()
                console.print("[bold cyan]🧩 问答结果[/bold cyan]")
                console.print(summary)
            else:
                console.print(f"[green]✓ 已完成问答[/green] {duration_str}")

        else:
            if len(output) > 200:
                console.print(f"[green]   ✓[/green] {output[:200]}... {duration_str}")
            else:
                console.print(f"[green]   ✓[/green] {output} {duration_str}")
    
    def _looks_like_code(self, text: str) -> bool:
        """简单判断文本是否像代码"""
        if not text.strip():
            return False
        # 检查是否包含常见的代码特征
        code_indicators = [
            "def ", "class ", "import ", "from ", "return ",
            "function ", "const ", "let ", "var ",
            "{", "}", "()", "[]", "=>", "->"
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in code_indicators)

    def _build_messages(self) -> list[dict]:
        """构建发送给 LLM 的消息列表"""
        messages = []

        # 系统提示
        if self.agent.system_prompt:
            messages.append({
                "role": "system",
                "content": self.agent.system_prompt
            })

        # 历史消息
        messages.extend(messages_to_openai_format(self.session.messages))

        return messages

    def _detect_doom_loop(self) -> bool:
        """检测 doom loop（相同工具调用重复3次）"""
        recent_calls = []
        for msg in reversed(self.session.messages):
            if msg.role != "assistant":
                continue
            for part in msg.parts:
                if isinstance(part, ToolPart):
                    recent_calls.append((
                        part.tool_call.tool_name,
                        json.dumps(part.tool_call.input, sort_keys=True)
                    ))
                    if len(recent_calls) >= DOOM_LOOP_THRESHOLD:
                        break
            if len(recent_calls) >= DOOM_LOOP_THRESHOLD:
                break

        if len(recent_calls) < DOOM_LOOP_THRESHOLD:
            return False

        first = recent_calls[0]
        return all(call == first for call in recent_calls)


# ============ 便捷函数 ============

async def run_agent(
    prompt: str,
    model: str = "openai/gpt-4o",
    agent_name: str = "build",
    working_dir: str = ".",
    session: Session = None
) -> AssistantMessage:
    """
    运行 Agent 的便捷函数

    Args:
        prompt: 用户输入
        model: 模型标识 (provider/model 格式)
        agent_name: Agent 名称
        working_dir: 工作目录
        session: 可选的现有会话

    Returns:
        助手消息
    """
    from .agent import AgentManager
    from .tools import create_default_registry
    from .permission import create_default_permission_manager
    from .session import SessionManager

    # 解析模型
    provider_id, model_id = parse_model(model)

    # 创建组件
    agent_manager = AgentManager(working_dir)
    agent_config = agent_manager.get(agent_name) or agent_manager.default_agent()

    tool_registry = create_default_registry()
    permission_manager = create_default_permission_manager()
    permission_manager.merge_rules(agent_config.permissions)

    provider = create_provider(provider_id, model_id)

    # 创建或使用会话
    if session is None:
        session_manager = SessionManager()
        session = session_manager.create(agent=agent_name, model=model)

    # 创建循环
    loop = AgentLoop(
        session=session,
        agent=agent_config,
        provider=provider,
        tool_registry=tool_registry,
        permission_manager=permission_manager,
        working_dir=working_dir
    )

    # 运行
    return await loop.run(prompt)
