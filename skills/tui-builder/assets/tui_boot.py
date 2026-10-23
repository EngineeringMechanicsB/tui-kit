#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tui_boot.py —— 所有脚本的启动层（Python 3.8+ / Win7 可用）

职责只有三件：
  1. 尝试打开 Windows 控制台的 VT 处理（Win10/11 默认是关的）
  2. 建一个配色统一的 rich Console（老控制台自动缩一列，防 Live 漂移）
  3. 给出 `plain()` 兜底：没装 rich 时也能正常输出

用法：
    from tui_boot import console, OK, ERR, WARN, INFO, LINE, banner

    banner("设备批量配置", "10.0.0.11")
    console.print(f"{OK} 完成")

设计约束（都是实机踩出来的，别改）：
  - Win7 的 SetConsoleMode 会「成功但位没置上」，必须回读确认
  - 写满最后一列时控制台自动换行，rich 再补 \\n 就多一行 → 宽度固定减 1
  - 老控制台只有 16 个色位，blue(#000080) 在黑底上几乎看不见 → 主题里不用蓝色
  - dim 在老控制台是直接清亮度位，等于把颜色弄没 → 用 bright_black 代替
"""
import os
import sys

# ---------------------------------------------------------------- 标记
# 全部 ASCII：老控制台、记事本、邮件都不会变成豆腐块
OK = "[OK]"
ERR = "[XX]"
WARN = "[!!]"
INFO = "[i]"
SKIP = "[--]"
LINE = "-" * 66

# ---------------------------------------------------------------- 主题
# 语义命名，换配色只改这一处。
# 不用 blue / dim，理由见文件头。
THEME = {
    "ok": "bold green",
    "err": "bold red",
    "warn": "bold yellow",
    "info": "cyan",
    "title": "bold magenta",
    "muted": "bright_black",
    "accent": "magenta",
}

IS_WIN = os.name == "nt"
IS_TTY = False


def enable_vt():
    """尝试为 stdout 打开 VT 处理，成功返回 True。

    Win10/11 的 conhost 支持 VT 但默认关闭；rich 一旦探测到没开就退回
    16 色老渲染。这里先自己打开，rich 就会走真彩色路径。
    Win7 上 SetConsoleMode 直接失败 → 返回 False，rich 自动走老控制台。
    """
    if not IS_WIN:
        return True
    try:
        import ctypes

        k = ctypes.windll.kernel32
        k.GetStdHandle.restype = ctypes.c_void_p
        handle = k.GetStdHandle(-11)          # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not k.GetConsoleMode(ctypes.c_void_p(handle), ctypes.byref(mode)):
            return False                       # 管道/重定向，不是控制台
        if mode.value & 0x0004:                # 已经开了
            return True
        if not k.SetConsoleMode(ctypes.c_void_p(handle), mode.value | 0x0004):
            return False                       # Win7：调用失败
        check = ctypes.c_uint32()
        k.GetConsoleMode(ctypes.c_void_p(handle), ctypes.byref(check))
        return bool(check.value & 0x0004)      # 回读，别信返回值
    except Exception:
        return False


def _fix_width(console):
    """控制台里把渲染宽度减 1，避免 Live 每帧往下漂一行。

    原因：写满最后一列时终端会自动换行，rich 以为还在本行，于是下一帧
    从下一行开始 → 屏幕逐步下滚。现代终端和老控制台都会遇到。
    """
    try:
        if console.is_terminal:
            console.width = max(40, console.width - 1)
    except Exception:
        pass
    return console


def make_console(record=False):
    """建 Console；没装 rich 时返回 None（调用方走 plain 输出）"""
    global IS_TTY
    try:
        from rich.console import Console
        from rich.theme import Theme
    except ImportError:
        return None
    console = Console(theme=Theme(THEME), record=record)
    IS_TTY = bool(getattr(console, "is_terminal", False))
    return _fix_width(console)


def plain(msg):
    """没有 rich 时的兜底输出：去掉方括号里的样式标记"""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", "replace").decode("utf-8", "replace"))
    return None


def setup_stdio():
    """非 tty 时把 stdio 改成 UTF-8（管道/重定向才不会乱码）。

    tty 下绝不动编码 —— Windows 本来就用 WriteConsoleW，改了反而坏。
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and not stream.isatty():
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


# ---------------------------------------------------------------- 便捷函数
def banner(console, title, subtitle=""):
    """顶部标题条；没 rich 时退化为 ==== 标题 ===="""
    from rich.panel import Panel
    from rich.text import Text

    body = Text(title, style="title")
    if subtitle:
        body.append("\n" + subtitle, style="muted")
    console.print(Panel(body, border_style="info", padding=(0, 2)))


def section(console, title):
    from rich.text import Text

    console.print(Text("── " + title + " " + "─" * max(0, 60 - len(title)), style="muted"))


def summary(console, ok, fail=0, skip=0, title="结果"):
    """收尾卡片：成功/失败/跳过。任何一项失败都用 warn 边框。"""
    from rich.panel import Panel
    from rich.text import Text

    bad = fail > 0
    body = Text.assemble(
        ("成功 ", "muted"), (str(ok), "ok"),
        ("   失败 ", "muted"), (str(fail), "err" if fail else "muted"),
        ("   跳过 ", "muted"), (str(skip), "warn" if skip else "muted"),
    )
    console.print(Panel(body, title=title,
                        border_style="warn" if bad else "ok", padding=(0, 2)))


if __name__ == "__main__":
    setup_stdio()
    vt = enable_vt()
    c = make_console()
    print("python", sys.version.split()[0], "vt", vt, "rich", bool(c), "tty", IS_TTY)
    if c:
        c.print("[ok]绿色[/] [warn]黄色[/] [err]红色[/] [info]青色[/] [muted]灰色[/]")
        banner(c, "tui_boot 自检", "这些颜色在 Win7 上会降级成 16 色，但都可读")
        summary(c, 3, 1, 2)
