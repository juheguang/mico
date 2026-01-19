"""
文件搜索工具
"""

from .base import BaseTool, ToolContext, ToolResult


class GlobTool(BaseTool):
    """文件搜索工具"""

    name = "glob"
    description = """Find files matching a glob pattern.
Use this to discover files in the project."""

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match files (e.g., '**/*.py', 'src/**/*.ts')"
                }
            },
            "required": ["pattern"]
        }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        pattern = params["pattern"]

        try:
            matches = list(ctx.working_dir.glob(pattern))
            # 限制结果数量
            max_results = 100
            truncated = len(matches) > max_results

            output_lines = [str(p.relative_to(ctx.working_dir)) for p in matches[:max_results]]
            if truncated:
                output_lines.append(f"... and {len(matches) - max_results} more files")

            return ToolResult(
                output="\n".join(output_lines) if output_lines else "No files found",
                title=f"glob: {pattern}",
                metadata={"count": len(matches), "truncated": truncated}
            )
        except Exception as e:
            return ToolResult(output=str(e), error=str(e))
