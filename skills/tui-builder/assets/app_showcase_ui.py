#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app_showcase_ui.py —— app_showcase 的 Textual 界面实现

单独用没意义，配套 app_showcase.run_tasks()。
"""
import os
import time

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button, DataTable, Footer, Header, Label, Markdown, ProgressBar,
    RichLog, Select, Static, TabbedContent, TabPane,
)

THEMES = [("Textual 深色", "textual-dark"), ("Textual 浅色", "textual-light"),
          ("Nord", "nord"), ("Gruvbox", "gruvbox"),
          ("Catppuccin", "catppuccin-mocha"), ("Tokyo Night", "tokyo-night")]


class ShowcaseApp(App):
    CSS = """
    #toolbar { height: auto; padding: 1 2 0 2; }
    #toolbar Button { margin-right: 1; }
    #toolbar Select { width: 24; margin-left: 2; }
    #toolbar Select#extra { width: 28; }
    #stats { height: 5; padding: 0 2; }
    .stat { width: 1fr; height: 100%; margin-right: 1;
            border: round $primary; content-align: center middle;
            background: $surface; }
    #tasks { height: 1fr; margin: 0 2; border: round $primary;
             background: $surface; }
    #progress-row { height: auto; padding: 0 2 1 2; }
    #pbar { width: 1fr; }
    #log { height: 1fr; margin: 1 2; border: round $accent;
           background: $surface; }
    #meta { padding: 1 2; color: $text-muted; }
    Screen.narrow #stats { height: 3; }
    Screen.narrow #toolbar Select { width: 18; }
    """

    BINDINGS = [("s", "start", "开始"), ("q", "quit", "退出"),
                ("t", "cycle_theme", "换主题")]

    def __init__(self, title, tasks, meta=None, log_path=None, report=None,
                 extra_select=None, on_extra=None):
        super().__init__()
        self.extra_select = extra_select      # (label, [(显示, 值), ...])
        self.on_extra = on_extra
        self.title = title
        self.sub_title = "tui-kit"
        self.tasks = list(tasks)
        self.meta = dict(meta or {})
        self.log_path = log_path
        self.report = report
        self.runner = None
        self.started_at = 0.0
        self.finished = False
        self.all_ok = False
        self.report_paths = {}
        self._shown = [False] * len(self.tasks)

    # -------------------------------------------------------------- 布局
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="tab-main"):
            with TabPane("任务", id="tab-main"):
                with Horizontal(id="toolbar"):
                    yield Button("开始", id="start", variant="success")
                    yield Button("中止", id="abort", variant="warning", disabled=True)
                    yield Button("重置", id="reset", variant="error")
                    yield Label("主题")
                    yield Select(THEMES, value="textual-dark", id="theme",
                                 allow_blank=False)
                    if self.extra_select:
                        yield Label(self.extra_select[0])
                        yield Select(self.extra_select[1], id="extra",
                                     allow_blank=False)
                with Horizontal(id="stats"):
                    for key, label in (("ok", "成功"), ("bad", "失败"),
                                       ("total", "步骤"), ("time", "耗时")):
                        yield Static("", id="stat-" + key, classes="stat")
                if self.meta:
                    yield Static("    ".join("%s：%s" % (k, v) for k, v in self.meta.items()),
                                 id="meta")
                yield DataTable(id="tasks")
                with Horizontal(id="progress-row"):
                    yield ProgressBar(total=max(1, len(self.tasks)), show_eta=False,
                                      id="pbar")
            with TabPane("日志", id="tab-log"):
                yield RichLog(id="log", markup=True, highlight=True,
                              wrap=True, max_lines=2000)
            with TabPane("报告", id="tab-report"):
                with VerticalScroll():
                    yield Markdown("按 s 开始。结束后这里显示报告路径与结果。",
                                   id="report")
            with TabPane("关于", id="tab-about"):
                yield Markdown(self._about(), id="about")
        yield Footer()

    def _about(self):
        lines = ["# %s" % self.TITLE, "", "## 配置", ""]
        for k, v in self.meta.items():
            lines.append("- **%s**：%s" % (k, v))
        if self.log_path:
            lines += ["", "日志：`%s`" % self.log_path]
        return "\n".join(lines)

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        self.cols = [
            table.add_column("步骤", width=28),
            table.add_column("状态", width=10),
            table.add_column("说明", width=44),
            table.add_column("耗时", width=8),
        ]
        table.zebra_stripes = True
        for i, (name, _) in enumerate(self.tasks):
            table.add_row(name, "-- 等待", "", "", key=str(i))
        self.set_interval(0.15, self._poll)
        self.set_interval(0.4, self._sync_layout)
        self._log("[bright_black]就绪 —— 按 s 开始[/]")
        self._update_stats()
        if os.environ.get("SHOWCASE_AUTO"):
            self.call_after_refresh(self.action_start)

    def _sync_layout(self):
        narrow = self.size.width < 90
        if self.screen.has_class("narrow") != narrow:
            self.screen.set_class(narrow, "narrow")

    # -------------------------------------------------------------- 动作
    def action_start(self) -> None:
        if self.runner and self.runner.running:
            return
        if self.finished:
            return
        from app_showcase import TaskRunner
        self.runner = TaskRunner(self.tasks)
        self.started_at = time.time()
        self.runner.start()
        self.query_one("#start").disabled = True
        self.query_one("#abort").disabled = False
        self._log("[bold green]开始执行[/]")

    def action_cycle_theme(self) -> None:
        names = [n for _, n in THEMES]
        idx = (names.index(self.theme) + 1) % len(names) if self.theme in names else 0
        self.theme = names[idx]
        self.query_one(Select).value = names[idx]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start":
            self.action_start()
        elif event.button.id == "abort":
            if self.runner:
                self.runner.abort()
                self._log("[yellow]已请求中止（当前步骤跑完就停）[/]")
        elif event.button.id == "reset":
            self._reset()

    def _reset(self):
        if self.runner and self.runner.running:
            return
        self.runner = None
        self._shown = [False] * len(self.tasks)
        self.finished = False
        self.all_ok = False
        table = self.query_one(DataTable)
        for i, (name, _) in enumerate(self.tasks):
            table.update_cell(str(i), self.cols[1], "-- 等待")
            table.update_cell(str(i), self.cols[2], "")
            table.update_cell(str(i), self.cols[3], "")
        self.query_one(ProgressBar).update(progress=0)
        self.query_one("#start").disabled = False
        self.query_one("#abort").disabled = True
        self._update_stats()

    @on(Select.Changed, "#extra")
    def _extra(self, event):
        if self.on_extra and event.value is not None:
            self.on_extra(event.value)

    @on(Select.Changed, "#theme")
    def _theme(self, event):
        if event.value:
            self.theme = event.value

    # -------------------------------------------------------------- 轮询
    def _poll(self):
        if not self.runner:
            return
        table = self.query_one(DataTable)
        for i, res in enumerate(self.runner.results):
            if res is None:
                if i == self.runner.current and self.runner.running:
                    table.update_cell(str(i), self.cols[1],
                                      "[yellow].. 进行中[/]")
                continue
            ok, detail, cost = res
            name = self.tasks[i][0]
            if self._shown[i]:
                continue
            self._shown[i] = True
            table.update_cell(str(i), self.cols[1],
                              "[green]OK 完成[/]" if ok else "[red]XX 失败[/]")
            table.update_cell(str(i), self.cols[2], detail)
            table.update_cell(str(i), self.cols[3], "%.1fs" % cost)
            self._log("[%s]%s[/] %s  %s  %.1fs" % (
                "green" if ok else "red", "OK" if ok else "XX", name, detail, cost))
            self.query_one(ProgressBar).advance(1)
        self._update_stats()
        if self.runner and not self.runner.running and not self.finished:
            self._finish()

    def _finish(self):
        self.finished = True
        ok = sum(1 for r in self.runner.results if r and r[0])
        bad = sum(1 for r in self.runner.results if r and not r[0])
        self.all_ok = bad == 0 and ok == len(self.tasks)
        self.query_one("#abort").disabled = True
        self.query_one("#start").disabled = True
        self.notify("完成：成功 %d，失败 %d" % (ok, bad), title="结束", timeout=5)
        self._log("[bold]执行结束：成功 %d 失败 %d[/]" % (ok, bad))

        lines = ["# 执行结果", "",
                 "**成功 %d / 失败 %d / 共 %d**" % (ok, bad, len(self.tasks)), "",
                 "| 步骤 | 结果 | 说明 | 耗时 |", "|---|---|---|---|"]
        for (name, _), r in zip(self.tasks, self.runner.results):
            if not r:
                lines.append("| %s | 跳过 | | |" % name)
                continue
            good, detail, cost = r
            lines.append("| %s | %s | %s | %.1fs |" % (
                name, "OK" if good else "FAIL", str(detail).replace("|", "\\|"), cost))
        if self.report:
            try:
                for name, okv, detail, cost in [
                        (n, r[0], r[1], r[2])
                        for (n, _), r in zip(self.tasks, self.runner.results) if r]:
                    self.report.step(name, okv, detail, cost)
                self.report_paths = self.report.finish() or {}
            except Exception as e:
                lines += ["", "报告生成失败：%s" % e]
        if self.report_paths:
            lines += ["", "## 报告文件", ""]
            for k, v in self.report_paths.items():
                lines.append("- **%s**：`%s`" % (k, v))
        self.query_one("#report", Markdown).update("\n".join(lines))
        self.query_one(TabbedContent).active = "tab-report"

    def _update_stats(self):
        results = self.runner.results if self.runner else [None] * len(self.tasks)
        ok = sum(1 for r in results if r and r[0])
        bad = sum(1 for r in results if r and not r[0])
        cost = (time.time() - self.started_at) if self.started_at else 0
        vals = {"ok": (ok, "bold green"), "bad": (bad, "bold red"),
                "total": (len(self.tasks), "bold cyan"),
                "time": ("%.0fs" % cost, "bold magenta")}
        labels = {"ok": "成功", "bad": "失败", "total": "步骤", "time": "耗时"}
        for key, (value, style) in vals.items():
            self.query_one("#stat-" + key, Static).update(
                "[bright_black]%s[/]\n[%s]%s[/]" % (labels[key], style, value))

    def _log(self, msg):
        try:
            self.query_one(RichLog).write(msg)
        except Exception:
            pass
        if self.log_path:
            import re
            plain = re.sub(r"\[/?[a-z_ ]+\]", "", msg)
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), plain))
            except Exception:
                pass
