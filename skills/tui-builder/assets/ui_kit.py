#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ui_kit.py —— 命令行脚本的通用界面组件（rich 优先，纯文本兜底）

覆盖 90% 运维脚本的需要，不用每次重写布局：
    ui = UI()
    ui.banner("设备批量配置", "10.0.0.11 · 3 个任务")
    idx = ui.menu(["开始配置", "查看现状", "退出"])          # 0/1/2，None=退出
    ui.table(["设备", "任务", "状态"], [["10.0.0.11:801", "改密码", "完成"]])
    ui.run_steps([("改密码", fn), ("恢复出厂", fn2)])        # 实时表格 + 进度条
    ui.summary(ok=2, fail=1)

回调约定（run_steps）：
    返回 True / (True, "说明") / "说明"  → 成功
    返回 False / (False, "说明") / 抛异常 → 失败（异常信息进说明列）

依赖：pip install "rich==14.0.0"   （Win7 + Python 3.8 必须锁这个版本）
"""
import os
import time

from tui_boot import (
    ERR, INFO, LINE, OK, SKIP, WARN,
    banner as _banner,
    make_console,
    section as _section,
    summary as _summary,
)

__all__ = ["UI", "OK", "ERR", "WARN", "INFO", "SKIP", "LINE"]


class UI(object):
    def __init__(self, log_path=None):
        self.console = make_console()
        self.rich = self.console is not None
        self.log_fp = None
        if log_path:
            d = os.path.dirname(log_path)
            if d and not os.path.isdir(d):
                os.makedirs(d)
            self.log_fp = open(log_path, "w", encoding="utf-8")
            self.log(u"=== 开始 %s ===" % time.strftime("%Y-%m-%d %H:%M:%S"))

    # ------------------------------------------------------------ 日志
    def _log(self, msg):
        """写日志文件（带时间戳）。没有日志文件时什么都不做。"""
        if not self.log_fp:
            return
        try:
            line = "[%s] %s\n" % (time.strftime("%H:%M:%S"),
                                  _strip_tags(str(msg)))
            self.log_fp.write(line)
            self.log_fp.flush()
        except Exception:
            pass

    def log(self, msg):
        """只写日志，不上屏"""
        self._log(msg)

    def close(self):
        if self.log_fp:
            try:
                self.log_fp.close()
            finally:
                self.log_fp = None

    # ------------------------------------------------------------ 基础
    def print(self, msg=""):
        """普通输出。有 rich 时自动解析 [ok]xxx[/] 这类主题标记"""
        self._log(msg)
        if self.rich:
            self.console.print(msg)
        else:
            print(_strip_tags(msg))

    def banner(self, title, subtitle=""):
        self._log("%s %s" % (title, subtitle))
        if self.rich:
            _banner(self.console, title, subtitle)
        else:
            print("\n" + LINE)
            print(title)
            if subtitle:
                print(subtitle)
            print(LINE)

    def section(self, title):
        self._log("-- %s --" % title)
        if self.rich:
            _section(self.console, title)
        else:
            print("\n-- %s %s" % (title, "-" * max(0, 60 - len(title))))

    def summary(self, ok, fail=0, skip=0, title="结果"):
        self._log("%s 成功 %d 失败 %d 跳过 %d" % (title, ok, fail, skip))
        if self.rich:
            _summary(self.console, ok, fail, skip, title)
        else:
            print(LINE)
            print("%s 成功 %d  失败 %d  跳过 %d" % (OK if not fail else WARN, ok, fail, skip))

    # ------------------------------------------------------------ 输入
    def menu(self, items, title="菜单", allow_multi=False):
        """编号菜单。items 可以是 str 或 (str, 说明)。

        返回：单选 → 下标（0 起）；多选 → 下标列表；输入 q/空 → None。
        不用 rich 的 Prompt，避免和 Live 抢屏幕；老控制台也稳。
        """
        self.section(title)
        for i, item in enumerate(items, 1):
            label = item[0] if isinstance(item, (tuple, list)) else item
            hint = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else ""
            line = "  %d) %s" % (i, label)
            if hint:
                line += "    " + hint
            self.print(line)
        tip = "  回车 = 全部，" if allow_multi else "  回车 = 默认，"
        self.print(tip + "q = 退出")
        try:
            raw = input("选择> ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if raw.lower() in ("q", "quit", "exit", "0"):
            return None
        if not raw:
            return list(range(len(items))) if allow_multi else 0
        nums = []
        for part in raw.replace(",", " ").split():
            if part.isdigit() and 1 <= int(part) <= len(items):
                nums.append(int(part) - 1)
        if not nums:
            self.print("%s 输入无效：%s" % (WARN, raw))
            return None
        return nums if allow_multi else nums[0]

    def confirm(self, question, default=False):
        suffix = " [Y/n] " if default else " [y/N] "
        try:
            raw = input(question + suffix).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return default
        if not raw:
            return default
        return raw in ("y", "yes", "是")

    def ask(self, question, default=""):
        tip = " [%s]" % default if default else ""
        try:
            raw = input(question + tip + ": ").strip()
        except (EOFError, KeyboardInterrupt):
            return default
        return raw or default

    # ------------------------------------------------------------ 表格
    def table(self, columns, rows, title=None, expand=True):
        """columns: ["设备", "状态"]；rows: [[...], ...]；单元格可放 rich 标记"""
        if not self.rich:
            cells = [[_strip_tags(str(c)) for c in r[:len(columns)]] for r in rows]
            widths = [_disp_width(str(c)) for c in columns]
            for r in cells:
                for i, cell in enumerate(r):
                    widths[i] = max(widths[i], _disp_width(cell))
            line = "  ".join(_pad(str(c), widths[i]) for i, c in enumerate(columns))
            print(line)
            print("-" * _disp_width(line))
            for r in cells:
                print("  ".join(_pad(c, widths[i]) for i, c in enumerate(r)))
            return

        from rich import box
        from rich.table import Table

        t = Table(title=title, box=box.SIMPLE_HEAD, expand=expand,
                  pad_edge=False, show_edge=False)
        for c in columns:
            t.add_column(c, no_wrap=True)
        for r in rows:
            t.add_row(*[str(x) for x in r])
        self.console.print(t)

    # ------------------------------------------------------------ 步骤执行
    def run_steps(self, steps, title="执行", log=None):
        """顺序执行 [(名称, 回调), ...]，实时显示状态表 + 总进度。

        返回 [(名称, 是否成功, 说明), ...]
        回调抛异常不会中断后续步骤，异常文本进说明列。
        """
        results = []
        if not self.rich:
            for name, fn in steps:
                print("%s %s ..." % (INFO, name), end="", flush=True)
                ok, detail = _call(fn)
                results.append((name, ok, detail))
                print("\r%s %s  %s  %s" % (OK if ok else ERR, name, "成功" if ok else "失败", detail))
                if log and detail:
                    log(name, ok, detail)
            return results

        from rich import box
        from rich.console import Group
        from rich.live import Live
        from rich.panel import Panel
        from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn
        from rich.table import Table
        from rich.text import Text

        progress = Progress(
            TextColumn("[muted]总进度[/]"),
            BarColumn(complete_style="ok", finished_style="ok", pulse_style="warn"),
            TaskProgressColumn(style="info"), expand=True, console=self.console,
        )
        task = progress.add_task("", total=len(steps))

        def render(state):
            t = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False, show_edge=False)
            t.add_column("步骤", no_wrap=True)
            t.add_column("状态", width=10)
            t.add_column("说明", style="muted")
            style = {"成功": "ok", "失败": "err", "进行中": "warn", "等待": "muted"}
            for name, status, detail in state:
                t.add_row(name, Text(status, style=style.get(status, "muted")), detail)
            return Panel(Group(t, progress), title=title,
                         border_style="info", box=box.ROUNDED, padding=(0, 1))

        state = [[name, "等待", ""] for name, _ in steps]
        with Live(render(state), console=self.console, refresh_per_second=10) as live:
            for i, (name, fn) in enumerate(steps):
                state[i][1] = "进行中"
                live.update(render(state))
                t0 = time.time()
                ok, detail = _call(fn)
                self._log("%s %s %s (%.1fs)" % ("OK" if ok else "XX", name, detail,
                                                time.time() - t0))
                state[i][1] = "成功" if ok else "失败"
                state[i][2] = detail
                results.append((name, ok, detail))
                progress.advance(task)
                live.update(render(state))
                if log:
                    log(name, ok, detail)
        return results

    # ------------------------------------------------------------ 长任务
    def spinner(self, text):
        """返回一个上下文管理器：块内代码执行期间显示转圈"""
        return _Spinner(self.console, text) if self.rich else _NullSpinner()


class _Spinner(object):
    def __init__(self, console, text):
        self.console = console
        self.text = text
        self.live = None

    def __enter__(self):
        from rich.live import Live
        from rich.spinner import Spinner

        self.live = Live(Spinner("dots", text=self.text), console=self.console,
                         refresh_per_second=10, transient=True)
        self.live.__enter__()
        return self

    def __exit__(self, *exc):
        if self.live:
            self.live.__exit__(*exc)
        return False


class _NullSpinner(object):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


# ---------------------------------------------------------------- 工具
def _call(fn):
    """把回调的各种返回值统一成 (ok, detail)"""
    try:
        out = fn()
    except Exception as e:                       # noqa: BLE001 - 要的就是兜底
        return False, str(e)[:120]
    if isinstance(out, tuple):
        ok = bool(out[0])
        detail = str(out[1]) if len(out) > 1 else ""
        return ok, detail
    if isinstance(out, str):
        return True, out
    return bool(out), ""


def _strip_tags(s):
    """把 rich 标记 [ok]xx[/] 变成 xx（plain 模式用）"""
    out = []
    i = 0
    while i < len(s):
        if s[i] == "[":
            j = s.find("]", i)
            if j != -1 and not s[i + 1:j].startswith(" "):
                i = j + 1
                continue
        out.append(s[i])
        i += 1
    return "".join(out).replace("[/]", "")


def _disp_width(s):
    """中文按 2 列算，用于 plain 模式对齐"""
    import unicodedata

    width = 0
    for ch in s:
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def _pad(s, width):
    return s + " " * max(0, width - _disp_width(s))


if __name__ == "__main__":
    ui = UI()
    ui.banner("ui_kit 自检", "菜单 / 表格 / 步骤 / 汇总")

    choice = ui.menu(["跑三个假步骤", "只看表格", "退出"], allow_multi=False)
    if choice is None or choice == 2:
        ui.summary(0, 0, 3)
        raise SystemExit(0)

    if choice == 1:
        ui.table(["设备", "任务", "状态"],
                 [["10.0.0.11:801", "改密码", "[ok]完成[/]"],
                  ["10.0.0.11:802", "改密码", "[warn]进行中[/]"]])
        raise SystemExit(0)

    def step1():
        time.sleep(0.4)
        return True, "已写入"

    def step2():
        time.sleep(0.4)
        return False, "连接超时"

    def step3():
        time.sleep(0.3)
        return "跳过（无需处理）"

    res = ui.run_steps([("改密码", step1), ("恢复出厂", step2), ("校验", step3)],
                       title="批量配置")
    ok = sum(1 for _, good, _ in res if good)
    ui.summary(ok, len(res) - ok, 0)
