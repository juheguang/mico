"""
工具显示美化模块 - 使用 Rich 组件美化工具输出
"""

import re
from pathlib import Path
from rich.panel import Panel
from rich.syntax import Syntax
from rich.tree import Tree
from rich.text import Text
from rich.box import ROUNDED, SIMPLE

from .console import console


def detect_language(file_path: str) -> str:
    """
    根据文件路径检测编程语言
    
    Args:
        file_path: 文件路径
        
    Returns:
        语言名称（用于 Syntax 高亮）
    """
    ext = Path(file_path).suffix.lower()
    lang_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".jsx": "jsx",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".fish": "bash",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".sql": "sql",
        ".md": "markdown",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".conf": "ini",
        ".txt": "text",
    }
    return lang_map.get(ext, "text")


def format_code_with_syntax(
    code: str,
    file_path: str = "unknown",
    language: str = None,
    line_numbers: bool = True
) -> Panel:
    """
    使用 Syntax 高亮显示代码
    
    Args:
        code: 代码内容
        file_path: 文件路径（用于检测语言和标题）
        language: 编程语言（如果为 None，则从文件路径检测）
        line_numbers: 是否显示行号
        
    Returns:
        Panel 组件
    """
    if not code.strip():
        return Panel(
            Text("[dim]空文件[/dim]"),
            title=f"[bold]📝 {Path(file_path).name}[/bold]",
            border_style="green"
        )
    
    # 检测语言
    if language is None:
        language = detect_language(file_path)
    
    # 计算行数
    lines = code.split("\n")
    line_count = len(lines)
    
    # 创建 Syntax 对象
    syntax = Syntax(
        code,
        language,
        theme="monokai",
        line_numbers=line_numbers,
        word_wrap=True,
        start_line=1
    )
    
    # 创建 Panel
    subtitle = f"[dim]{line_count} 行[/dim]"
    return Panel(
        syntax,
        title=f"[bold]📝 {Path(file_path).name}[/bold]",
        subtitle=subtitle,
        border_style="green",
        box=ROUNDED
    )


def format_directory_tree(list_output: str, root_path: str = ".") -> Tree:
    """
    将 list 工具的输出转换为 Tree 结构
    
    Args:
        list_output: list 工具的输出（每行一个路径）
        root_path: 根路径
        
    Returns:
        Tree 组件
    """
    lines = list_output.strip().split("\n") if list_output.strip() else []
    if not lines:
        return Tree("[dim]空目录[/dim]", guide_style="dim")
    
    # 解析路径
    items = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 尝试解析格式：可能是 "file.txt" 或 "dir/" 或完整路径
        path = Path(line)
        items.append(path)
    
    if not items:
        return Tree("[dim]空目录[/dim]", guide_style="dim")
    
    # 构建树结构
    root = Tree(
        f"📁 [bold blue]{Path(root_path).name or root_path}/[/bold blue]",
        guide_style="dim"
    )
    
    # 按路径排序
    items.sort(key=lambda p: (str(p).count("/"), str(p)))
    
    # 构建节点映射
    nodes = {Path(root_path): root}
    
    for item in items:
        # 确保是相对于 root_path 的路径
        if not str(item).startswith(str(root_path)) and not item.is_absolute():
            item = Path(root_path) / item
        
        # 获取父目录
        parent = item.parent
        if parent == item:  # 根目录
            parent = Path(root_path)
        
        # 确保父节点存在
        current = parent
        path_parts = []
        while current != Path(root_path) and current != Path("."):
            path_parts.insert(0, current)
            current = current.parent
        
        for part in path_parts:
            if part not in nodes:
                # 找到父节点
                part_parent = part.parent
                if part_parent == part:
                    part_parent = Path(root_path)
                
                if part_parent in nodes:
                    node = nodes[part_parent].add(
                        f"📁 [blue]{part.name}/[/blue]"
                    )
                    nodes[part] = node
        
        # 添加当前项
        if parent in nodes:
            if item.is_dir() or str(item).endswith("/"):
                icon = "📁"
                style = "blue"
                name = item.name if item.name else str(item)
            else:
                icon = "📄"
                style = "green"
                name = item.name
            
            nodes[parent].add(f"{icon} [{style}]{name}[/{style}]")
    
    return root


def format_list_output_simple(list_output: str) -> Tree:
    """
    简化版：直接将 list 输出转换为树（假设是简单的文件列表）
    目录在前，文件在后
    
    Args:
        list_output: list 工具的输出（格式：📁 name 或 📄 name）
        
    Returns:
        Tree 组件
    """
    lines = list_output.strip().split("\n") if list_output.strip() else []
    if not lines:
        return Tree("[dim]空目录[/dim]", guide_style="dim")
    
    root = Tree("📁 [bold blue]当前目录[/bold blue]", guide_style="dim")
    
    # 分离目录和文件
    dirs = []
    files = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # list 工具的输出格式是 "📁 name" 或 "📄 name"
        # 提取图标和名称
        if line.startswith("📁"):
            name = line[1:].strip()
            dirs.append(f"[blue]{name}[/blue]")
        elif line.startswith("📄"):
            name = line[1:].strip()
            files.append(f"[green]{name}[/green]")
        else:
            # 如果没有图标，根据后缀判断
            if line.endswith("/") or line.endswith("\\"):
                dirs.append(f"[blue]{line}[/blue]")
            else:
                files.append(f"[green]{line}[/green]")
    
    # 先添加目录，再添加文件
    for item in dirs:
        root.add(item)
    for item in files:
        root.add(item)
    
    return root


def format_diff(old_string: str, new_string: str, file_path: str = "unknown") -> Panel:
    """
    显示代码差异（edit 工具的 old_string vs new_string）
    
    Args:
        old_string: 旧内容
        new_string: 新内容
        file_path: 文件路径
        
    Returns:
        Panel 组件
    """
    if not old_string:
        # 新文件，只显示新内容
        return format_code_with_syntax(new_string, file_path)
    
    # 计算差异
    old_lines = old_string.split("\n")
    new_lines = new_string.split("\n")
    
    diff_text = Text()
    
    # 简单的行对行比较（可以后续优化为更智能的 diff）
    max_lines = max(len(old_lines), len(new_lines))
    added_count = 0
    removed_count = 0
    
    for i in range(max_lines):
        old_line = old_lines[i] if i < len(old_lines) else None
        new_line = new_lines[i] if i < len(new_lines) else None
        
        if old_line != new_line:
            if old_line is not None:
                diff_text.append(f"  {i+1:4} ", style="dim")
                diff_text.append(f"-{old_line}\n", style="red")
                removed_count += 1
            if new_line is not None:
                diff_text.append(f"  {i+1:4} ", style="dim")
                diff_text.append(f"+{new_line}\n", style="green")
                added_count += 1
        else:
            if old_line is not None:
                diff_text.append(f"  {i+1:4} ", style="dim")
                diff_text.append(f" {old_line}\n", style="dim")
    
    subtitle = f"[dim]+{added_count} -{removed_count}[/dim]"
    return Panel(
        diff_text,
        title=f"[bold yellow]📝 Edit: {Path(file_path).name}[/bold yellow]",
        subtitle=subtitle,
        border_style="yellow",
        box=ROUNDED
    )
