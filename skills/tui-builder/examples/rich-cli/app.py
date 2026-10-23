#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""示例：设备巡检（rich + 配置 + 自动模式 + 报告）

演示一个"能交付"的最小完整脚本，业务很简单，外围一样不少：

    python app.py                 # 交互菜单
    python app.py --auto          # 按配置里的 steps 跑完
    python app.py --steps ping    # 只跑指定步骤
    python app.py --dry-run       # 只打印计划
    python app.py --list-hosts    # 列出目标

首次运行生成 app_config.json（带注释）。命令行参数优先。
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "..", "assets"))
sys.path.insert(0, ASSETS)

from config_kit import Config            # noqa: E402
from report_kit import Reporter          # noqa: E402
from ui_kit import UI                    # noqa: E402

DEFAULTS = {
    "hosts": ["192.168.77.230", "192.168.77.231"],
    "timeout_ms": 1000,
    "steps": ["ping", "detail"],
    "report": True,
    "report_dir": "reports",
    "log_dir": "logs",
}
DOCS = {
    "hosts": "要巡检的 IP 列表（一行一个）",
    "timeout_ms": "单次 ping 超时（毫秒）",
    "steps": "默认步骤：ping（存活）/ detail（延迟与丢包）",
    "report": "true = 生成 Markdown + HTML + JSON 报告",
    "report_dir": "报告目录（相对脚本）",
    "log_dir": "日志目录（相对脚本）",
}
ALL_STEPS = ["ping", "detail"]
STEP_NAMES = {"ping": "存活检测", "detail": "详情采集"}


def ping(host, timeout_ms):
    """Windows / Linux 通用：只看退出码，不解析输出（避开中文编码问题）"""
    if os.name == "nt":
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), host]
    t0 = time.time()
    try:
        rc = subprocess.call(cmd, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    except Exception as e:
        return False, "ping 无法执行：%s" % e, 0.0
    return rc == 0, ("可达" if rc == 0 else "不可达"), (time.time() - t0) * 1000


def build_tasks(cfg, selected):
    tasks = []
    for host in cfg["hosts"]:
        if "ping" in selected:
            tasks.append(("ping %s" % host,
                          lambda h=host: _ping_step(cfg, h)))
        if "detail" in selected:
            tasks.append(("采集 %s" % host,
                          lambda h=host: _detail_step(cfg, h)))
    return tasks


def _ping_step(cfg, host):
    ok, detail, cost = ping(host, cfg["timeout_ms"])
    return ok, "%s（%.0f ms）" % (detail, cost)


def _detail_step(cfg, host):
    ok, detail, cost = ping(host, cfg["timeout_ms"])
    if not ok:
        return False, "跳过：主机不可达"
    return True, "延迟 %.0f ms" % cost


def main():
    cfg = Config("app", DEFAULTS, DOCS).load()

    import argparse
    ap = argparse.ArgumentParser(description="设备巡检示例")
    ap.add_argument("--auto", action="store_true", help="自动模式")
    ap.add_argument("--steps", default="", help="逗号分隔：ping,detail")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划")
    ap.add_argument("--list-hosts", action="store_true", help="列出目标")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args()

    ui = UI()
    if args.no_color:
        ui.console.no_color = True

    selected = ([s.strip() for s in args.steps.split(",") if s.strip()]
                or list(cfg["steps"]))
    bad = [s for s in selected if s not in ALL_STEPS]
    if bad:
        ui.print("[XX] 不认识的步骤：%s（可选 %s）" % (",".join(bad), ",".join(ALL_STEPS)))
        return 2

    ui.banner("设备巡检", "%d 台 · %s" % (len(cfg["hosts"]), cfg["report_dir"]))

    if args.list_hosts:
        ui.table(["#", "IP"], [[i + 1, h] for i, h in enumerate(cfg["hosts"])])
        return 0

    tasks = build_tasks(cfg, selected)

    if args.dry_run:
        ui.table(["步骤", "说明"], [[n, "会执行"] for n, _ in tasks])
        ui.print("[i] dry-run，未执行")
        return 0

    if not args.auto and sys.stdin.isatty():
        idx = ui.menu(["开始巡检", "只看计划", "退出"])
        if idx is None or idx == 2:
            return 0
        if idx == 1:
            ui.table(["步骤", "说明"], [[n, "会执行"] for n, _ in tasks])
            return 0

    reporter = None
    if cfg["report"]:
        reporter = Reporter("设备巡检", target="%d 台" % len(cfg["hosts"]),
                            out_dir=os.path.join(HERE, cfg["report_dir"]),
                            log_dir=os.path.join(HERE, cfg["log_dir"]),
                            meta={"步骤": ",".join(selected)}).start()
        ui.log_fp = reporter.log_fp

    results = ui.run_steps(tasks, title="巡检过程")
    ok = sum(1 for _, good, _ in results if good)
    ui.summary(ok, len(results) - ok, 0)

    if reporter:
        for name, good, detail in results:
            reporter.step(name, good, detail)
        ui.log_fp = None
        paths = reporter.finish()
        ui.print("[i] 报告：%s" % paths["html"])

    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
