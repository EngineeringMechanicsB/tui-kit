#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""<工具名> —— 一句话说清这个脚本干什么

时间：<YYYY-MM-DD>
作者：<你>

用法：
    python app.py                      # 交互菜单
    python app.py --host 10.0.0.11     # 非交互
    python app.py --dry-run            # 只看计划，不执行
    python app.py --no-color           # 关颜色

依赖：pip install "rich==14.0.0"      # Win7 目标必须锁 14.0.0
"""
import argparse
import sys
import time

from ui_kit import UI, LINE          # 同目录：tui_boot.py + ui_kit.py


# ---------------------------------------------------------------- 业务
# 规则：业务函数不 print、不碰 UI，只返回 (ok, detail)。
# 这样 rich 界面、textual 界面、测试代码都能复用。
def step_login(host):
    if not host:
        return False, "缺少 host"
    time.sleep(0.2)                  # 真实实现换成实际动作
    return True, "已连接"


def step_change(host, new_pwd):
    time.sleep(0.3)
    return True, "密码已改为 %s" % new_pwd


def step_verify(host):
    time.sleep(0.2)
    return True, "回读一致"


# ---------------------------------------------------------------- 编排
def build_steps(args):
    return [
        ("登录设备", lambda: step_login(args.host)),
        ("修改配置", lambda: step_change(args.host, args.new_pwd)),
        ("回读校验", lambda: step_verify(args.host)),
    ]


def main():
    ap = argparse.ArgumentParser(description="<工具名>")
    ap.add_argument("--host", default="10.0.0.11", help="设备 IP")
    ap.add_argument("--new-pwd", default="Wtoe_8746", help="新密码")
    ap.add_argument("--dry-run", action="store_true", help="只显示计划")
    ap.add_argument("--no-color", action="store_true", help="关闭颜色")
    ap.add_argument("--yes", action="store_true", help="不弹菜单，直接执行")
    args = ap.parse_args()

    ui = UI()
    if args.no_color and ui.rich:
        ui.console.no_color = True

    ui.banner("<工具名>", "%s · %d 个步骤" % (args.host, 3))

    steps = build_steps(args)

    if args.dry_run:
        ui.table(["步骤", "目标"], [[name, args.host] for name, _ in steps])
        ui.print("%s dry-run，未执行" % "[i]")
        return 0

    if not args.yes and sys.stdin.isatty():
        choice = ui.menu(["开始执行", "只看计划", "退出"])
        if choice is None or choice == 2:
            return 0
        if choice == 1:
            ui.table(["步骤", "目标"], [[n, args.host] for n, _ in steps])
            return 0

    results = ui.run_steps(steps, title="执行过程")
    ok = sum(1 for _, good, _ in results if good)
    ui.summary(ok, len(results) - ok, 0)

    # 退出码：失败非 0，方便批处理判断
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n中断")
        sys.exit(130)
