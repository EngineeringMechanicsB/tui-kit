#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app_skeleton.py —— Textual 全屏应用的起步骨架（Win10/11）

复制这个文件改三个 TODO 就能变成自己的工具：
  1. TODO-1  改 TITLE / 数据源
  2. TODO-2  compose() 里换掉表格列
  3. TODO-3  action_start() 里换成真实业务

已经内置的、你大概率不用再写的东西：
  Header/Footer、标签页、彩色表格、进度条、RichLog、统计卡片、
  主题循环、模态确认、输入筛选、窄终端自适应、按键绑定

运行： python app_skeleton.py
按键： s 开始   p 暂停   r 重置   t 换主题   q 退出
"""
import os
import random
import sys

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label, LoadingIndicator,
    ProgressBar, RichLog, Select, Static, Switch, TabbedContent, TabPane,
)

from tui_boot import enable_vt                 # 同目录；也可复制那 40 行进项目

# TODO-1: 数据源
DEVICES = [
    ("10.0.0.11", 801, "改密码"),
    ("10.0.0.11", 802, "改密码"),
    ("10.0.0.11", 803, "恢复出厂"),
]

THEMES = [("Textual 深色", "textual-dark"), ("Textual 浅色", "textual-light"),
          ("Nord", "nord"), ("Gruvbox", "gruvbox"),
          ("Catppuccin", "catppuccin-mocha"), ("Tokyo Night", "tokyo-night")]


class Confirm(ModalScreen):
    """通用确认框：push_screen(Confirm("确定？"), callback)"""

    CSS = """
    Confirm { align: center middle; background: $background 60%; }
    #dialog { width: 50; height: auto; padding: 1 2;
              border: thick $error; background: $surface; }
    #buttons { height: auto; align-horizontal: right; }
    #buttons Button { margin-left: 2; }
    """

    def __init__(self, question):
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.question)
            with Horizontal(id="buttons"):
                yield Button("取消", id="cancel")
                yield Button("确认", id="confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


class Main(App):
    TITLE = "运维控制台"                    # TODO-1
    SUB_TITLE = "app_skeleton 模板"

    CSS = """
    #toolbar { height: auto; padding: 1 2 0 2; }
    #toolbar Button { margin-right: 1; }
    #toolbar Select { width: 26; margin-left: 2; }
    #stats { height: 5; padding: 0 2; }
    .stat { width: 1fr; height: 100%; margin-right: 1;
            border: round $primary; content-align: center middle;
            background: $surface; }
    #devices { height: 1fr; margin: 0 2; border: round $primary;
               background: $surface; }
    #filter-row { height: auto; padding: 0 2 1 2; }
    #filter { width: 40; background: $panel; border: tall $primary 30%; }
    #filter:focus { border: tall $accent; }
    #progress-row { height: auto; padding: 0 2 1 2; }
    #pbar { width: 1fr; }
    #indicator { width: 6; height: 1; margin-left: 2; }
    #log { height: 1fr; margin: 1 2; border: round $accent;
           background: $surface; }

    /* 窄终端：统计卡压扁、输入框变短，表格自动出横向滚动条 */
    Screen.narrow #stats { height: 3; }
    Screen.narrow .stat { border: round $primary 40%; }
    Screen.narrow #filter { width: 24; }
    """

    BINDINGS = [("s", "start", "开始"), ("p", "pause", "暂停"),
                ("r", "reset", "重置"), ("t", "cycle_theme", "换主题"),
                ("q", "quit", "退出")]

    def __init__(self):
        super().__init__()
        self.rows = [{"ip": ip, "port": port, "task": t, "pct": 0,
                      "status": "等待", "note": ""} for ip, port, t in DEVICES]
        self.cursor = 0
        self.running = False
        self.ok = 0
        self.bad = 0
        self._timer = None

    # -------------------------------------------------------------- 布局
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="tab-main"):
            with TabPane("任务", id="tab-main"):
                with Horizontal(id="toolbar"):
                    yield Button("开始", id="start", variant="success")
                    yield Button("暂停", id="pause", variant="warning")
                    yield Button("重置", id="reset", variant="error")
                    yield Switch(value=True, id="autoscroll")
                    yield Label("主题")
                    yield Select(THEMES, value="textual-dark", id="theme",
                                 allow_blank=False)
                with Horizontal(id="stats"):
                    for key, label in (("ok", "成功"), ("bad", "失败"),
                                       ("total", "总数"), ("pct", "总进度")):
                        yield Static("", id="stat-" + key, classes="stat")
                with Horizontal(id="filter-row"):
                    yield Input(placeholder="筛选：IP / 端口 / 任务…", id="filter")
                yield DataTable(id="devices")           # TODO-2
                with Horizontal(id="progress-row"):
                    yield ProgressBar(total=len(DEVICES), show_eta=False, id="pbar")
                    yield LoadingIndicator(id="indicator")
            with TabPane("日志", id="tab-log"):
                yield RichLog(id="log", markup=True, highlight=True,
                              wrap=True, max_lines=1000)
            with TabPane("关于", id="tab-about"):
                yield Static("在这里写使用说明。", id="about")
        yield Footer()

    # -------------------------------------------------------------- 初始化
    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        self.cols = [
            table.add_column("设备", width=16),
            table.add_column("端口", width=6),
            table.add_column("任务", width=12),
            table.add_column("进度", width=6),
            table.add_column("状态", width=10),
            table.add_column("说明", width=24),
        ]
        table.cursor_type = "row"
        table.zebra_stripes = True
        for d in self.rows:
            table.add_row(d["ip"], str(d["port"]), d["task"], "0%",
                          "-- 等待", "", key=self._key(d))
        self.query_one(LoadingIndicator).display = False
        self.set_interval(0.4, self._sync_layout)       # 自适应，别用 Resize 事件
        self._update_stats()

    def _key(self, d):
        return "%s:%s" % (d["ip"], d["port"])

    def _sync_layout(self):
        narrow = self.size.width < 90
        if self.screen.has_class("narrow") != narrow:
            self.screen.set_class(narrow, "narrow")

    # -------------------------------------------------------------- 交互
    def on_button_pressed(self, event: Button.Pressed) -> None:
        {"start": self.action_start, "pause": self.action_pause,
         "reset": self.action_reset}.get(event.button.id, lambda: None)()

    @on(Select.Changed, "#theme")
    def _theme(self, event):
        if event.value:
            self.theme = event.value

    @on(Input.Changed, "#filter")
    def _filter(self, event):
        needle = event.value.strip().lower()
        table = self.query_one(DataTable)
        for d in self.rows:
            visible = needle in self._key(d).lower() or needle in d["task"].lower()
            try:
                table.set_row_visibility(self._key(d), visible)
            except Exception:
                pass

    # -------------------------------------------------------------- 动作
    def action_start(self) -> None:
        if self.running or self.cursor >= len(self.rows):
            return
        self.running = True
        self.query_one(LoadingIndicator).display = True
        self.query_one("#start").disabled = True
        self._timer = self.set_interval(0.12, self._tick)

    def action_pause(self) -> None:
        if not self.running:
            return
        self.running = False
        if self._timer:
            self._timer.stop()
        self.query_one(LoadingIndicator).display = False
        self.query_one("#start").disabled = False

    def action_reset(self) -> None:
        def done(ok):
            if not ok:
                return
            self.action_pause()
            for d in self.rows:
                d.update(pct=0, status="等待", note="")
            self.cursor = self.ok = self.bad = 0
            table = self.query_one(DataTable)
            for d in self.rows:
                table.update_cell(self._key(d), self.cols[3], "0%")
                table.update_cell(self._key(d), self.cols[4], "-- 等待")
                table.update_cell(self._key(d), self.cols[5], "")
            self.query_one(ProgressBar).update(progress=0)
            self.query_one("#start").disabled = False
            self._update_stats()

        self.push_screen(Confirm("确认重置全部？"), done)

    def action_cycle_theme(self) -> None:
        names = [n for _, n in THEMES]
        idx = (names.index(self.theme) + 1) % len(names) if self.theme in names else 0
        self.theme = names[idx]
        self.query_one(Select).value = names[idx]

    # -------------------------------------------------------------- 业务
    def _tick(self) -> None:
        """TODO-3: 换成真实步骤。这里只是演示状态推进。"""
        if not self.running:
            return
        d = self.rows[self.cursor]
        d["pct"] = min(100, d["pct"] + random.choice([5, 8, 10]))
        d["status"] = "进行中"
        if d["pct"] >= 100:
            good = random.random() > 0.15
            d["status"] = "完成" if good else "失败"
            d["note"] = "已写入" if good else "连接超时"
            self.ok += 1 if good else 0
            self.bad += 0 if good else 1
            self.cursor += 1
            self.query_one(ProgressBar).advance(1)
            self.query_one(RichLog).write(
                "[%s]%s[/] %s %s %s" % ("green" if good else "red",
                                        "OK" if good else "XX",
                                        self._key(d), d["task"], d["status"]))
            if self.cursor >= len(self.rows):
                self.running = False
                if self._timer:
                    self._timer.stop()
                self.query_one(LoadingIndicator).display = False
                self.notify("完成：成功 %d，失败 %d" % (self.ok, self.bad),
                            title="结束", timeout=4)
        self._render(d)
        self._update_stats()

    def _render(self, d):
        table = self.query_one(DataTable)
        color = {"完成": "green", "失败": "red", "进行中": "yellow"}.get(
            d["status"], "bright_black")
        icon = {"完成": "OK", "失败": "XX", "进行中": ".."}.get(d["status"], "--")
        table.update_cell(self._key(d), self.cols[3], "%d%%" % d["pct"])
        table.update_cell(self._key(d), self.cols[4], "[%s]%s %s[/]"
                          % (color, icon, d["status"]))
        table.update_cell(self._key(d), self.cols[5], d["note"])

    def _update_stats(self):
        pct = sum(d["pct"] for d in self.rows) // max(1, len(self.rows))
        values = {"ok": (self.ok, "bold green"), "bad": (self.bad, "bold red"),
                  "total": (len(self.rows), "bold cyan"), "pct": ("%d%%" % pct, "bold magenta")}
        labels = {"ok": "成功", "bad": "失败", "total": "总数", "pct": "总进度"}
        for key, (value, style) in values.items():
            self.query_one("#stat-" + key, Static).update(
                "[bright_black]%s[/]\n[%s]%s[/]" % (labels[key], style, value))


def main():
    if os.name == "nt" and not enable_vt():
        print("[XX] 需要支持 VT 的终端（Windows Terminal / Win10+）。")
        print("     Win7 请用 rich 版脚本（ui_kit.py + run_steps）。")
        return 1
    Main().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
