#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report_kit.py —— 运行日志 + 测试报告（Markdown / HTML / JSON）

一次运行产三样东西，放在同一个目录：

    reports/20261023_140501_10.0.0.11.md      人看的报告
    reports/20261023_140501_10.0.0.11.html    浏览器打开更好看（单文件，无外链）
    reports/20261023_140501_10.0.0.11.json    机器读的结果
    logs/20261023_140501_10.0.0.11.log        全过程日志（带时间戳）

用法：
    from report_kit import Reporter
    rep = Reporter("牌识升级", target="10.0.0.11", out_dir="reports", log_dir="logs")
    rep.start()
    rep.log("开始连接")
    rep.step("上传", True, "12.3 MB / 3.2s", seconds=3.2)
    rep.step("安装", False, "install.sh 返回 1", seconds=1.1)
    rep.finish()                       # 自动写 md/html/json，返回路径字典

设计约束：
  - 纯标准库（Win7 的 Python 3.8 也能跑）
  - HTML 单文件、内联样式，不依赖网络
  - 中文用 UTF-8，Windows 记事本可读（HTML 带 meta charset）
"""
import html
import json
import os
import time

__all__ = ["Reporter"]


def _safe(name):
    keep = []
    for ch in str(name):
        keep.append(ch if (ch.isalnum() or ch in "._-") else "_")
    return "".join(keep)[:80] or "run"


class Reporter(object):
    def __init__(self, app, target="", out_dir="reports", log_dir="logs",
                 meta=None, stamp=None):
        self.app = app
        self.target = target or "local"
        self.stamp = stamp or time.strftime("%Y%m%d_%H%M%S")
        self.base = "%s_%s" % (self.stamp, _safe(self.target))
        self.out_dir = out_dir
        self.log_dir = log_dir
        self.meta = dict(meta or {})
        self.steps = []            # [(名称, ok, 说明, 秒)]
        self.t0 = None
        self.elapsed = 0.0
        self.log_fp = None
        self.log_path = ""

    # ------------------------------------------------------------ 生命周期
    def start(self):
        self.t0 = time.time()
        for d in (self.out_dir, self.log_dir):
            if d and not os.path.isdir(d):
                os.makedirs(d)
        self.log_path = os.path.join(self.log_dir, self.base + ".log")
        self.log_fp = open(self.log_path, "w", encoding="utf-8")
        self.log("=" * 60)
        self.log("%s 开始  target=%s" % (self.app, self.target))
        for k, v in self.meta.items():
            self.log("%s: %s" % (k, v))
        self.log("=" * 60)
        return self

    def log(self, msg):
        """写一行带时间戳的日志；同时原样打到终端"""
        line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
        try:
            print(line)
        except Exception:
            pass
        if self.log_fp:
            try:
                self.log_fp.write(line + "\n")
                self.log_fp.flush()
            except Exception:
                pass
        return line

    def step(self, name, ok, detail="", seconds=None):
        self.steps.append((name, bool(ok), detail, seconds))
        mark = "[OK]" if ok else "[XX]"
        cost = "  %.1fs" % seconds if seconds is not None else ""
        self.log("%s %s  %s%s" % (mark, name, detail, cost))
        return self

    def finish(self):
        self.elapsed = time.time() - (self.t0 or time.time())
        ok = sum(1 for _, good, _, _ in self.steps if good)
        fail = len(self.steps) - ok
        self.log("-" * 60)
        self.log("结束：成功 %d  失败 %d  耗时 %.1fs" % (ok, fail, self.elapsed))
        if self.log_fp:
            try:
                self.log_fp.close()
            finally:
                self.log_fp = None
        paths = {
            "log": self.log_path,
            "md": os.path.join(self.out_dir, self.base + ".md"),
            "html": os.path.join(self.out_dir, self.base + ".html"),
            "json": os.path.join(self.out_dir, self.base + ".json"),
        }
        self._write_md(paths["md"])
        self._write_html(paths["html"])
        self._write_json(paths["json"])
        return paths

    # ------------------------------------------------------------ 输出
    def _write_md(self, path):
        ok = sum(1 for _, good, _, _ in self.steps if good)
        lines = ["# %s 报告" % self.app, "",
                 "- 目标：`%s`" % self.target,
                 "- 时间：%s" % self.stamp,
                 "- 耗时：%.1f 秒" % self.elapsed,
                 "- 结果：**成功 %d / 失败 %d**" % (ok, len(self.steps) - ok), ""]
        for k, v in self.meta.items():
            lines.append("- %s：%s" % (k, v))
        lines += ["", "## 步骤", "", "| 步骤 | 结果 | 说明 | 耗时 |",
                  "|---|---|---|---|"]
        for name, good, detail, sec in self.steps:
            lines.append("| %s | %s | %s | %s |" % (
                name, "OK" if good else "FAIL", detail.replace("|", "\\|"),
                "%.1fs" % sec if sec is not None else ""))
        lines += ["", "日志：`%s`" % self.log_path, ""]
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))

    def _write_json(self, path):
        data = {
            "app": self.app, "target": self.target, "stamp": self.stamp,
            "elapsed": round(self.elapsed, 2), "meta": self.meta,
            "steps": [{"name": n, "ok": g, "detail": d,
                       "seconds": None if s is None else round(s, 2)}
                      for n, g, d, s in self.steps],
            "ok": sum(1 for _, g, _, _ in self.steps if g),
            "fail": sum(1 for _, g, _, _ in self.steps if not g),
            "log": self.log_path,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _write_html(self, path):
        ok = sum(1 for _, good, _, _ in self.steps if good)
        fail = len(self.steps) - ok
        rows = []
        for name, good, detail, sec in self.steps:
            color = "#1a7f37" if good else "#c62828"
            bg = "#f6fef9" if good else "#fff5f5"
            rows.append(
                '<tr style="background:%s"><td>%s</td>'
                '<td style="color:%s;font-weight:600">%s</td>'
                '<td>%s</td><td class="num">%s</td></tr>' % (
                    bg, html.escape(name), color, "OK" if good else "FAIL",
                    html.escape(detail), "" if sec is None else "%.1fs" % sec))
        meta_rows = "".join(
            '<tr><th>%s</th><td>%s</td></tr>' % (html.escape(k), html.escape(str(v)))
            for k, v in self.meta.items())
        doc = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>%(app)s 报告</title>
<style>
 body{font-family:"Segoe UI","Microsoft YaHei",sans-serif;background:#f4f6f8;
      color:#1f2328;margin:0;padding:32px}
 .card{max-width:860px;margin:0 auto;background:#fff;border-radius:12px;
       box-shadow:0 2px 12px rgba(0,0,0,.08);padding:28px 32px}
 h1{margin:0 0 6px;font-size:22px}
 .sub{color:#59636e;font-size:13px;margin-bottom:20px}
 .stats{display:flex;gap:12px;margin:18px 0}
 .stat{flex:1;border:1px solid #d8dee4;border-radius:10px;padding:12px 16px}
 .stat b{display:block;font-size:24px;margin-top:4px}
 .good{color:#1a7f37}.bad{color:#c62828}
 table{width:100%%;border-collapse:collapse;font-size:14px}
 th,td{text-align:left;padding:9px 10px;border-bottom:1px solid #eaeef2}
 th{color:#59636e;font-weight:600;background:#f6f8fa}
 .num{text-align:right;color:#59636e}
 .meta{margin-top:22px;font-size:13px}
 .meta th{width:140px;background:none;border-bottom:1px solid #eaeef2}
 footer{margin-top:22px;color:#8c959f;font-size:12px}
</style></head><body><div class="card">
<h1>%(app)s 报告</h1>
<div class="sub">目标 %(target)s · %(stamp)s · 耗时 %(elapsed).1f 秒</div>
<div class="stats">
 <div class="stat">成功<b class="good">%(ok)d</b></div>
 <div class="stat">失败<b class="bad">%(fail)d</b></div>
 <div class="stat">步骤<b>%(total)d</b></div>
</div>
<table><thead><tr><th>步骤</th><th>结果</th><th>说明</th><th>耗时</th></tr></thead>
<tbody>%(rows)s</tbody></table>
<table class="meta">%(meta)s</table>
<footer>日志：%(log)s</footer>
</div></body></html>""" % {
            "app": html.escape(self.app), "target": html.escape(self.target),
            "stamp": self.stamp, "elapsed": self.elapsed, "ok": ok,
            "fail": fail, "total": len(self.steps), "rows": "".join(rows),
            "meta": meta_rows, "log": html.escape(self.log_path)}
        with open(path, "w", encoding="utf-8") as f:
            f.write(doc)


if __name__ == "__main__":
    r = Reporter("report_kit 自检", target="10.0.0.11",
                 out_dir="_demo_reports", log_dir="_demo_logs")
    r.start()
    r.log("假装在连接设备")
    r.step("上传", True, "12.3 MB / 3.2s", seconds=3.2)
    r.step("安装", False, "install.sh 退出码 1", seconds=1.1)
    paths = r.finish()
    for k, v in paths.items():
        print(k, "->", v)
