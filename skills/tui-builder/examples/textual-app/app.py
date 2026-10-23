#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""示例：全屏执行器（textual，Win10/11）

业务步骤是假的，重点是外壳怎么接：
    python app.py              # 全屏，点"开始"
    python app.py --auto       # 全屏并自动开始
    python app.py --rich       # 没有 textual 时的降级路径

依赖：pip install textual rich
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "..", "assets"))
sys.path.insert(0, ASSETS)

from report_kit import Reporter          # noqa: E402
from ui_kit import UI                    # noqa: E402


def check_env():
    time.sleep(0.6)
    return True, "Python %s" % sys.version.split()[0]


def prepare():
    time.sleep(0.8)
    return True, "临时目录已就绪"


def install():
    time.sleep(1.0)
    return False, "模拟失败：权限不足"


def verify():
    time.sleep(0.5)
    return True, "校验通过"


TASKS = [("检查环境", check_env), ("准备", prepare),
         ("安装", install), ("验证", verify)]


def main():
    ap = argparse.ArgumentParser(description="全屏执行器示例")
    ap.add_argument("--auto", action="store_true", help="启动后自动开始")
    ap.add_argument("--rich", action="store_true", help="强制普通输出")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划")
    args = ap.parse_args()

    if args.dry_run:
        for name, _ in TASKS:
            print("  - %s" % name)
        return 0

    reporter = Reporter("示例任务", target="localhost",
                        out_dir=os.path.join(HERE, "reports"),
                        log_dir=os.path.join(HERE, "logs")).start()

    if args.rich:
        ui = UI()
        ui.banner("示例任务", "rich 降级路径")
        results = ui.run_steps(TASKS)
        for name, ok, detail in results:
            reporter.step(name, ok, detail)
        paths = reporter.finish()
        print("报告：", paths["html"])
        return 0 if all(ok for _, ok, _ in results) else 1

    try:
        from app_showcase import run_tasks
    except ImportError:
        print("[XX] 没装 textual：pip install textual（或用 --rich）")
        return 2

    ok = run_tasks("示例任务", TASKS,
                   meta={"目标": "localhost", "步骤": len(TASKS)},
                   log_path=reporter.log_path,
                   report=reporter,
                   autostart=args.auto)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
