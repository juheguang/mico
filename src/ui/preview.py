"""
编辑预览组件 - 流式显示正在写入的代码
"""

from pathlib import Path
from rich.live import Live
from rich.text import Text

from .console import console


class EditStreamPreview:
    """
    Edit 工具的流式预览状态机
    
    在 LLM 生成 edit 工具参数的过程中，实时解析 JSON 并显示 new_string 内容。
    使用滑动窗口只显示最后 5 行，避免刷屏。
    """
    
    # 状态定义
    STATE_SEARCHING = "searching"      # 寻找 "new_string" 键
    STATE_BEFORE_VALUE = "before_value"  # 找到键，等待值开始
    STATE_IN_STRING = "in_string"      # 在 new_string 值内部
    STATE_DONE = "done"                # 完成
    
    # 显示配置
    WINDOW_SIZE = 5  # 滑动窗口大小
    
    def __init__(self, file_path: str = "unknown"):
        self.state = self.STATE_SEARCHING
        self.buffer = ""
        self.escape_next = False
        self.line_buffer = ""
        self.line_count = 0
        self.char_count = 0
        self.header_shown = False
        self.file_path = file_path
        
        # 滑动窗口：存储最近的行 (line_num, content)
        self.recent_lines: list[tuple[int, str]] = []
        
        # Live 组件
        self._live = None
        self._live_started = False
        
    def process_delta(self, delta: str) -> None:
        """处理增量 JSON 字符串片段"""
        if not delta or self.state == self.STATE_DONE:
            return
            
        for char in delta:
            self._process_char(char)
    
    def _process_char(self, char: str) -> None:
        """处理单个字符"""
        # 处理转义字符
        if self.escape_next:
            self.escape_next = False
            if self.state == self.STATE_IN_STRING:
                # JSON 转义字符处理
                if char == 'n':
                    self.char_count += 1  # 换行也算一个字符
                    self._emit_line()     # 输出当前行
                elif char == 't':
                    self.line_buffer += '    '  # Tab 转为 4 空格
                    self.char_count += 1
                elif char == 'r':
                    pass  # 忽略 \r
                elif char == '"':
                    self.line_buffer += '"'
                    self.char_count += 1
                elif char == '\\':
                    self.line_buffer += '\\'
                    self.char_count += 1
                elif char == '/':
                    self.line_buffer += '/'
                    self.char_count += 1
                elif char == 'u':
                    # Unicode 转义，简化处理
                    self.line_buffer += '\\u'
                    self.char_count += 2
                else:
                    self.line_buffer += char
                    self.char_count += 1
            return
        
        # 检测转义开始
        if char == '\\':
            self.escape_next = True
            return
        
        # 状态机逻辑
        if self.state == self.STATE_SEARCHING:
            self.buffer += char
            # 检测 "new_string": 或 "new_string" :
            if '"new_string"' in self.buffer:
                # 继续检查后面是否有冒号
                if ':' in self.buffer.split('"new_string"')[-1]:
                    self.state = self.STATE_BEFORE_VALUE
                    self.buffer = ""
                    
        elif self.state == self.STATE_BEFORE_VALUE:
            # 等待值的开始引号
            if char == '"':
                self.state = self.STATE_IN_STRING
                self._start_live()
                
        elif self.state == self.STATE_IN_STRING:
            if char == '"':
                # 遇到未转义的引号，值结束
                self._emit_final_line()
                self._stop_live()
                self.state = self.STATE_DONE
            else:
                self.line_buffer += char
                self.char_count += 1
                # 实时更新当前行显示
                self._update_display()
    
    def _start_live(self) -> None:
        """启动 Live 显示"""
        if not self._live_started:
            console.print()  # 换行
            self._live = Live(
                self._build_display(),
                console=console,
                refresh_per_second=15,
                transient=True  # 结束后清除，然后打印最终结果
            )
            self._live.start()
            self._live_started = True
    
    def _stop_live(self) -> None:
        """停止 Live 显示并打印最终结果"""
        if self._live and self._live_started:
            self._live.stop()
            self._live_started = False
            
            # 打印最终结果（静态）
            self._print_final_result()
    
    def _build_display(self) -> Text:
        """构建当前显示内容"""
        lines = []
        
        # 头部
        lines.append(f"[dim]   ┌─ 正在写入: {self.file_path} ({self.line_count} 行, {self.char_count} 字符) ─[/dim]")
        
        # 如果有省略的行
        if self.line_count > self.WINDOW_SIZE:
            lines.append(f"[dim]   │ ... ({self.line_count - self.WINDOW_SIZE} 行已省略) ...[/dim]")
        
        # 显示最近的行
        for line_num, content in self.recent_lines:
            line_display = content[:100] + "..." if len(content) > 100 else content
            line_display = line_display.replace("[", "\\[")
            lines.append(f"[dim]   │[/dim] [cyan]{line_num:4}[/cyan] [dim]│[/dim] {line_display}")
        
        # 显示当前正在输入的行（如果有）
        if self.line_buffer:
            current_line_num = self.line_count + 1
            line_display = self.line_buffer[:100] + "..." if len(self.line_buffer) > 100 else self.line_buffer
            line_display = line_display.replace("[", "\\[")
            lines.append(f"[dim]   │[/dim] [cyan]{current_line_num:4}[/cyan] [dim]│[/dim] {line_display}[blink]▌[/blink]")
        
        # 底部
        lines.append(f"[dim]   └─────────────────────────────────────────[/dim]")
        
        return Text.from_markup("\n".join(lines))
    
    def _update_display(self) -> None:
        """更新 Live 显示"""
        if self._live and self._live_started:
            self._live.update(self._build_display())
    
    def _emit_line(self) -> None:
        """完成一行，加入滑动窗口"""
        self.line_count += 1
        line = self.line_buffer
        self.line_buffer = ""
        
        # 加入滑动窗口
        self.recent_lines.append((self.line_count, line))
        
        # 保持窗口大小
        if len(self.recent_lines) > self.WINDOW_SIZE:
            self.recent_lines.pop(0)
        
        # 更新显示
        self._update_display()
    
    def _emit_final_line(self) -> None:
        """输出最后一行（如果有内容）"""
        if self.line_buffer:
            self.line_count += 1
            line = self.line_buffer
            self.recent_lines.append((self.line_count, line))
            if len(self.recent_lines) > self.WINDOW_SIZE:
                self.recent_lines.pop(0)
            self.line_buffer = ""
    
    def _print_final_result(self) -> None:
        """打印最终静态结果"""
        lines = []
        
        # 头部
        lines.append(f"[dim]   ┌─ 写入完成: {self.file_path} ─────────────[/dim]")
        
        # 如果有省略的行
        if self.line_count > self.WINDOW_SIZE:
            lines.append(f"[dim]   │ ... ({self.line_count - self.WINDOW_SIZE} 行已省略) ...[/dim]")
        
        # 显示最近的行
        for line_num, content in self.recent_lines:
            line_display = content[:100] + "..." if len(content) > 100 else content
            line_display = line_display.replace("[", "\\[")
            lines.append(f"[dim]   │[/dim] [cyan]{line_num:4}[/cyan] [dim]│[/dim] {line_display}")
        
        # 底部统计
        lines.append(f"[dim]   └─ 共 {self.line_count} 行, {self.char_count} 字符 ────────────[/dim]")
        
        console.print("\n".join(lines))
        console.print()
