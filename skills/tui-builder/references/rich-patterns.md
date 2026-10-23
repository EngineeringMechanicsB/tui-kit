# rich 常用配方

先建 Console（不要直接 `Console()`）：

```python
from tui_boot import make_console
console = make_console()          # 主题 + 宽度修正 + 老控制台适配
```

主题里已有的语义名：`ok / err / warn / info / title / muted / accent`。
写 `console.print("[ok]完成[/]")` 即可，不要写死 `green`。

## 1. 标题卡

```python
from rich.panel import Panel
from rich.text import Text

console.print(Panel(
    Text.assemble(("设备批量配置", "title"), ("\n10.0.0.11 · 3 个任务", "muted")),
    border_style="info", padding=(0, 2),
))
```

## 2. 步骤表 + 总进度（最常用）

`ui_kit.UI.run_steps` 已经封装好，直接：

```python
ui.run_steps([
    ("改 Web 密码", lambda: (True, "已写入")),
    ("改海康密码", lambda: (False, "连接超时")),
], title="批量配置")
```

自己写时的骨架：

```python
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn
from rich.table import Table

def render(state, progress):
    t = Table(box=box.SIMPLE_HEAD, expand=True)
    ...
    return Panel(Group(t, progress), title="执行", border_style="info")

with Live(render(state, progress), console=console, refresh_per_second=10) as live:
    for i, (name, fn) in enumerate(steps):
        state[i]["status"] = "进行中"
        live.update(render(state, progress))
        ok, detail = fn()
        state[i].update(status="成功" if ok else "失败", detail=detail)
        progress.advance(task)
        live.update(render(state, progress))
```

关键点：
- Live 的 renderable 高度变化时 rich 会自己补行，不用管
- 回调里**不要** print，会插进 Live 的绘制区
- `refresh_per_second` 8–12 足够；再高只会闪

## 3. 表格

```python
from rich import box
from rich.table import Table

t = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False, show_edge=False)
t.add_column("设备", no_wrap=True)
t.add_column("状态")
t.add_row("10.0.0.11:801", "[ok]完成[/]")
console.print(t)
```

- 中文列宽 rich 自己算（按 2 列），**不要**手动 ljust
- `expand=True` 撑满；列多时改 `expand=False`
- 单元格可以放 `Text`，做两种颜色拼接

## 4. 结果卡

```python
from rich.panel import Panel
from rich.text import Text

console.print(Panel(
    Text.assemble(("成功 ", "muted"), ("3", "ok"),
                  ("   失败 ", "muted"), ("1", "err")),
    title="结果", border_style="warn", padding=(0, 2),
))
```

## 5. 转圈（单步长任务）

```python
from rich.live import Live
from rich.spinner import Spinner

with Live(Spinner("dots", text="正在连接 10.0.0.11"),
          console=console, transient=True, refresh_per_second=10):
    do_something()
```

`transient=True` 结束后不留残影，适合夹在普通输出中间。

## 6. 进度条（已知总量）

```python
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

with Progress(TextColumn("[muted]下载[/]"), BarColumn(), TimeElapsedColumn(),
              console=console) as p:
    task = p.add_task("", total=100)
    for i in range(100):
        p.advance(task)
```

## 7. 键盘输入

只用内建 `input()`：

```python
choice = input("选择> ").strip()
```

不要引 `readchar` / `msvcrt` / `pwinput`：
- Win7 老控制台 + 中文输入法下方向键常常发两次事件
- 打包后多一个依赖，收益极低

需要密码不回显时用 `getpass`（Windows 下可用），但注意管道调用会失败，要 try/except。

## 8. 富文本静态内容

```python
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.tree import Tree

console.print(Markdown("# 标题\n- 列表\n\n| a | b |\n|---|---|\n| 1 | 2 |"))
console.print(Syntax(open("x.py").read(), "python", line_numbers=True, theme="ansi_dark"))
tree = Tree("配置")
tree.add("onvif.cfg").add("passwd")
console.print(tree)
```

`theme="ansi_dark"` 在 16 色控制台上也能看；其他主题依赖真彩。

## 9. 两栏布局

```python
from rich.columns import Columns

console.print(Columns([panel_a, panel_b], expand=True, equal=True))
```

宽度不够时 rich 会自动堆叠，但判断依据是渲染宽度，窗口变窄需要重新渲染
（Live 每次 update 会重算，普通 print 不会）。

## 10. 常见错误

| 现象 | 原因 | 修法 |
|---|---|---|
| 每次刷新往下滚一行 | 渲染宽度 = 终端宽度 | `console.width -= 1` |
| 颜色不对/发暗 | VT 没开，走 16 色 | 先 `enable_vt()` 再建 Console |
| 中文列错位 | 自己用了 `ljust` | 交给 rich 的 Table |
| Live 里文字重复 | 回调里 print 了 | 所有输出走 `live.update` |
| 打包后颜色没了 | 输出被重定向 | 正常，重定向时 rich 自动关色 |

## 11. 关闭颜色

用户机器上颜色冲突时可以给个开关：

```python
import os
console = make_console()
if os.environ.get("NO_COLOR") or "--no-color" in sys.argv:
    console.no_color = True
```

`NO_COLOR` 是社区约定，尊重它没坏处。
