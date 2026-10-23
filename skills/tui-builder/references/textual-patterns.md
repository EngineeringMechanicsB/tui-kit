# Textual 应用配方（仅 Win10/11）

## 0. 先看限制

- 需要 Python ≥3.9（textual 8.x）
- 需要 VT 终端。**Windows Terminal 正常；老 conhost 中文会错位**，
  这是 conhost 的宽字符模型问题（Textual issue #5456 / #4974），不是代码 bug
- 打包后 ~21 MB（Python 3.12 实测）
- 目标机有 Win7 → 不要用，改用 rich 版

启动前先 `enable_vt()`，失败就直接提示改用 rich 版（见 `assets/app_skeleton.py` 的 `main`）。

## 1. 最小可运行

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static

class Main(App):
    TITLE = "工具名"
    BINDINGS = [("q", "quit", "退出")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("hello")
        yield Footer()

Main().run()
```

## 2. 骨架文件

直接复制 `assets/app_skeleton.py`，改三个 TODO：

1. `DEVICES` / 数据源
2. `compose()` 里的 `DataTable` 列
3. `_tick()` 的业务逻辑

已经内置：标签页、按钮、开关、下拉、统计卡、进度条、加载动画、
RichLog、模态确认、输入筛选、主题循环、自适应、按键。

## 3. 布局与 CSS

```python
CSS = """
#toolbar { height: auto; padding: 1 2 0 2; }
#stats  { height: 5; padding: 0 2; }
.stat   { width: 1fr; height: 100%; margin-right: 1;
          border: round $primary; content-align: center middle;
          background: $surface; }
DataTable { height: 1fr; }
"""
```

要点：
- 高度用 `1fr` 占剩余空间，`auto` 按内容
- 颜色用主题变量 `$primary $surface $accent $text-muted`，换主题自动适配
- `border: round $primary` 比默认方框柔和
- 容器 `Horizontal / Vertical / Grid / VerticalScroll`

## 4. 表格

```python
table = self.query_one(DataTable)
cols = table.add_columns(
    ("设备", 16),  # (标题, 宽度) 也可以逐列 add_column(label, width=...)
)
table.cursor_type = "row"
table.zebra_stripes = True
table.add_row("10.0.0.11", "改密码", "0%", "[yellow]进行中[/]", key="801")
table.update_cell("801", cols[3], "[green]完成[/]")
```

- **必须给列固定宽度**，自动宽度在中文下会算窄，导致竖排
- `update_cell` 的 column 参数在 8.x 必须是 `ColumnKey`，不能是字符串
- `set_row_visibility(key, False)` 做筛选

## 5. 日志

```python
from textual.widgets import RichLog

log = self.query_one(RichLog)
log.write("[green]OK[/] 10.0.0.11:801 改密码 完成")
```

配置 `RichLog(markup=True, highlight=True, wrap=True, max_lines=1000)`。

## 6. 事件与按键

```python
from textual import on

def on_button_pressed(self, event: Button.Pressed) -> None:
    if event.button.id == "start":
        self.action_start()

@on(Select.Changed, "#theme")
def _theme(self, event):
    self.theme = event.value
```

- 自定义按键在 `BINDINGS` 里加 `("s", "start", "开始")`，配 `action_start()`
- 内置命令面板 `Ctrl+P` 不用写

## 7. 后台任务

短任务用 `set_interval`；长任务用 worker：

```python
def action_start(self):
    self.run_worker(self._work(), exclusive=True)

async def _work(self):
    import asyncio
    for i in range(10):
        await asyncio.sleep(0.2)
        self.query_one(ProgressBar).advance(1)
```

`exclusive=True` 自动取消上一个 worker，避免连点两次。

## 8. 模态框

```python
class Confirm(ModalScreen):
    CSS = "Confirm { align: center middle; background: $background 60%; }"
    def compose(self):
        yield Button("确认", id="ok", variant="error")
    def on_button_pressed(self, e):
        self.dismiss(e.button.id == "ok")

# 调用
self.push_screen(Confirm(), lambda ok: self.action_reset() if ok else None)
```

## 9. 自适应（重要）

**不要用 `on_resize`**：Windows conpty 下拖动窗口/最大化不触发该事件。
用轮询：

```python
def on_mount(self):
    self.set_interval(0.4, self._sync_layout)

def _sync_layout(self):
    narrow = self.size.width < 90
    if self.screen.has_class("narrow") != narrow:
        self.screen.set_class(narrow, "narrow")
```

CSS：

```css
Screen.narrow #stats { height: 3; }
Screen.narrow #filter { width: 24; }
```

Textual 的 CSS **不支持 `@media`**，只能用 class。

## 10. 主题

```python
self.theme = "nord"          # 直接赋值
THEMES = ["textual-dark", "textual-light", "nord", "gruvbox",
          "catppuccin-mocha", "tokyo-night", "dracula", "monokai",
          "solarized-dark", "solarized-light"]
```

做成下拉框体验最好，切换即时生效。

## 11. 测试（不用真终端）

```python
import asyncio
async def main():
    app = Main()
    async with app.run_test(size=(120, 34)) as pilot:
        await pilot.pause()
        app.action_start()
        await pilot.pause(1.0)
        assert app.ok >= 0
        await pilot.resize_terminal(70, 30)
        await pilot.pause(0.6)
        assert app.screen.has_class("narrow")
asyncio.run(main())
```

- `export_screenshot()` 返回 SVG，可在无 GUI 环境核对布局
- 对话框：`app.action_reset(); app.screen.dismiss(True)`

## 12. 打包 textual

PyInstaller 能打，但注意：

- `--onefile` 体积约 21 MB，启动 1–2 秒（解压）
- 不需要额外 hiddenimports，textual 自带 hook
- **只能给 Win10/11**：Python 3.9+ 打出来的 exe 在 Win7 上起不来
- 建议同时提供 rich 版入口：`app.py --tui` 走 textual，默认走 rich

## 13. 常见坑

| 现象 | 原因 | 修法 |
|---|---|---|
| 中文竖排 | 列宽自动计算偏小 | 给每列固定 width |
| 状态列错位 | `update_cell` 用了字符串列名 | 用 `add_column` 返回的 key |
| 窗口最大化后布局不变 | Resize 事件没来 | 轮询 `self.size` |
| 老 conhost 字符残影 | conhost 宽字符模型 | 用 Windows Terminal |
| 启动报 VT 相关错误 | 老终端 | 捕获后提示用 rich 版 |
| 按钮连点重复执行 | 没有 exclusive worker | `run_worker(..., exclusive=True)` |

## 14. 与 rich 共用业务逻辑

```python
# core.py —— 不 import 任何 UI
def change_password(host, old, new):
    ...
    return True, "已写入"

# app.py —— textual 调 core
# run_all.py —— rich 调 core
```

UI 层只负责把 `(ok, detail)` 画出来，这样 Win7/Win10 两条线共用同一套业务。
