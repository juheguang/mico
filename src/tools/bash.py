"""
Bash 命令执行工具
"""

import asyncio
from .base import BaseTool, ToolContext, ToolResult


class BashTool(BaseTool):
    """Bash 命令执行工具"""

    name = "bash"
    description = """Execute a bash command in the shell.
Use this for running commands, scripts, or interacting with the system.
The command runs in the current working directory."""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute"
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what this command does"
                }
            },
            "required": ["command", "description"]
        }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        command = params["command"]
        description = params.get("description", "")

        # 检查权限
        await ctx.ask_permission("bash", [command], {"command": command})

        try:
            # 异步执行命令
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(ctx.working_dir)
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    output=f"Command timed out after {self.timeout}s",
                    title=description,
                    error="timeout"
                )

            output = stdout.decode() + stderr.decode()
            return ToolResult(
                output=output,
                title=description,
                metadata={"exit_code": process.returncode}
            )

        except Exception as e:
            return ToolResult(
                output=str(e),
                title=description,
                error=str(e)
            )
