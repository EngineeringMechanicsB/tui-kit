#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""<工具名> —— 一句话说清这个脚本干什么

时间：<YYYY-MM-DD>

运行：
    python app.py                      # 交互菜单
    python app.py --auto               # 自动模式：按配置里的 steps 跑完就退出
    python app.py --steps login,change # 只跑指定步骤
    python app.py --tui                # 全屏界面（Win10/11）
    python app.py --dry-run            # 只看计划

第一次运行会在脚本目录生成 <工具名>_config.json（带注释，可直接改）。
以后每次运行都读它；命令行参数优先。

依赖：pip install "rich==14.0.0"       # Win7 必须锁 14.0.0
可选：pip install textual              # 仅 --tui
"""
import argparse
import os
import sys
import time

from config_kit import Config
from report_kit import Reporter
from ui_kit import UI

# ---------------------------------------------------------------- 配置
DEFAULTS = {
    "host": "10.0.0.11",
    "port": 22,
    "user": "root",
    "password": "wtoe_123456",
    "steps": ["login", "change", "verify"],
    "report": True,
    "report_dir": "reports",
    "log_dir": "logs",
}

DOCS = {
    "host": "设备 IP；连不上时先 ping 确认在线",
    "port": "SSH 端口",
    "user": "SSH 账号",
    "password": "SSH 密码（现场会改，别写死在代码里）",
    "steps": "默认执行哪些步骤：login / change / verify",
    "report": "true = 每次运行生成 Markdown + HTML + JSON 报告",
    "report_dir": "报告存放目录（相对脚本目录）",
    "log_dir": "日志存放目录（相对脚本目录）",
}

ALL_STEPS = ["login", "change", "verify"]
STEP_NAMES = {"login": "登录设备", "change": "修改配置", "verify": "回读校验"}


# ---------------------------------------------------------------- 业务
def step_login(cfg):
    if not cfg["host"]:
        return False, "缺少 host"
    time.sleep(0.3)
    return True, "已连接 %s" % cfg["host"]


def step_change(cfg):
    time.sleep(0.5)
    return True, "配置已写入"


def step_verify(cfg):
    time.sleep(0.2)
    return True, "回读一致"


STEP_FUNCS = {"login": step_login, "change": step_change, "verify": step_verify}


def build_tasks(cfg, selected):
    return [(STEP_NAMES[key], (lambda k=key: STEP_FUNCS[k](cfg)))
            for key in ALL_STEPS if key in selected]


# ---------------------------------------------------------------- 入口
def parse_args(cfg):
    ap = argparse.ArgumentParser(description="<工具名>")
    ap.add_argument("--config", default=cfg.path, help="配置文件路径")
    ap.add_argument("--host", default=None, help="覆盖配置里的设备 IP")
    ap.add_argument("--steps", default="", help="逗号分隔，只跑这几步：" + ",".join(ALL_STEPS))
    ap.add_argument("--auto", action="store_true", help="自动模式：不弹菜单")
    ap.add_argument("--tui", action="store_true", help="全屏界面（需要 textual，Win10/11）")
    ap.add_argument("--report", dest="report", action="store_true", help="生成报告")
    ap.add_argument("--no-report", dest="report", action="store_false")
    ap.add_argument("--dry-run", action="store_true", help="只显示计划")
    ap.add_argument("--no-color", action="store_true")
    ap.set_defaults(report=None)
    return ap.parse_args()


def main():
    cfg = Config("<工具名>", DEFAULTS, DOCS).load()
    args = parse_args(cfg)

    # 命令行覆盖写回内存（不自动落盘，避免把一次性调试参数永久化）
    if args.host:
        cfg["host"] = args.host
    selected = ([s.strip() for s in args.steps.split(",") if s.strip()]
                or list(cfg["steps"]))
    bad = [s for s in selected if s not in ALL_STEPS]
    if bad:
        print("不认识的步骤：%s（可选 %s）" % (",".join(bad), ",".join(ALL_STEPS)))
        return 2

    ui = UI()
    if args.no_color and ui.rich:
        ui.console.no_color = True

    ui.banner("<工具名>", "%s · %s" % (cfg["host"], " → ".join(STEP_NAMES[s] for s in selected)))

    tasks = build_tasks(cfg, selected)

    if args.dry_run:
        ui.table(["步骤", "说明"], [[name, "会执行"] for name, _ in tasks])
        ui.print("[i] dry-run，未连接设备")
        ui.close()
        return 0

    # ---- 交互菜单（自动模式 / 非终端时跳过）
    if not args.auto and sys.stdin.isatty():
        idx = ui.menu(["开始执行", "只看计划", "退出"], allow_multi=False)
        if idx is None or idx == 2:
            ui.close()
            return 0
        if idx == 1:
            ui.table(["步骤", "说明"], [[name, "会执行"] for name, _ in tasks])
            ui.close()
            return 0

    # ---- 报告与日志
    want_report = cfg["report"] if args.report is None else args.report
    base = os.path.dirname(os.path.abspath(__file__))
    reporter = None
    if want_report:
        reporter = Reporter(
            "<工具名>", target=cfg["host"],
            out_dir=os.path.join(base, cfg["report_dir"]),
            log_dir=os.path.join(base, cfg["log_dir"]),
            meta={"设备": cfg["host"], "步骤": ",".join(selected)},
        ).start()
    if reporter and reporter.log_fp:
        ui.log_fp = reporter.log_fp          # UI 输出同时进日志

    # ---- 全屏模式
    if args.tui:
        from app_showcase import run_tasks
        ok = run_tasks("<工具名>", tasks,
                       meta={"设备": cfg["host"], "步骤": len(tasks)},
                       log_path=reporter.log_path if reporter else None,
                       report=reporter)
        ui.close()
        return 0 if ok else 1

    # ---- 常规 rich 模式
    results = ui.run_steps(tasks, title="执行过程")
    ok = sum(1 for _, good, _ in results if good)
    ui.summary(ok, len(results) - ok, 0)

    if reporter:
        for name, good, detail in results:
            reporter.step(name, good, detail)
        paths = reporter.finish()
        ui.print("[i] 报告：%s" % paths.get("html", ""))
        ui.print("[i] 日志：%s" % paths.get("log", ""))
        ui.log_fp = None                     # 已由 reporter 关闭
    ui.close()
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n中断")
        sys.exit(130)
