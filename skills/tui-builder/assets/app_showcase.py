#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app_showcase.py —— 通用「步骤执行器」全屏界面（Textual，Win10/11）

不是骨架，是成品：把一串 (名称, 回调) 丢进来就能跑，界面和 demo 一样。

    from app_showcase import run_tasks

    run_tasks(
        "牌识相机固件升级",
        [("上传升级包", do_upload), ("安装", do_install), ("重启", do_reboot)],
        meta={"设备": "192.168.77.230", "升级包": "V1.2.0"},
        log_path="logs/20261023.log",
        report=reporter,          # report_kit.Reporter，可选
    )

回调约定：返回 True / (True, "说明") / "说明" 算成功，
False / (False, "说明") / 抛异常算失败。

单独运行（内部演示）：python app_showcase.py
按键：s 开始  q 退出  t 换主题
"""
import os
import sys
import threading
import time

from tui_boot import enable_vt

SWITCHES_FALLBACK = {"start": True}


class TaskRunner(object):
    """把步骤列表包装成线程可执行的对象（不依赖 textual，便于测试）"""

    def __init__(self, tasks):
        self.tasks = list(tasks)
        self.results = [None] * len(self.tasks)
        self.current = 0
        self.running = False
        self.aborted = False
        self._thread = None

    def start(self):
        self.running = True
        self.aborted = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        for i, (name, fn) in enumerate(self.tasks):
            if self.aborted:
                break
            self.current = i
            t0 = time.time()
            try:
                out = fn()
            except Exception as e:                     # noqa: BLE001
                self.results[i] = (False, str(e)[:160], time.time() - t0)
                continue
            if isinstance(out, tuple):
                ok = bool(out[0])
                detail = str(out[1]) if len(out) > 1 else ""
            elif isinstance(out, str):
                ok, detail = True, out
            else:
                ok, detail = bool(out), ""
            self.results[i] = (ok, detail, time.time() - t0)
        self.running = False

    def abort(self):
        self.aborted = True


def run_tasks(title, tasks, meta=None, log_path=None, report=None,
              extra_select=None, on_extra=None, autostart=False):
    """启动全屏界面；返回 True 表示全部成功

    extra_select/on_extra: 额外下拉框（如选升级包），(标题, [(显示, 值)]) + 回调
    """
    from app_showcase_ui import ShowcaseApp
    app = ShowcaseApp(title, tasks, meta=meta, log_path=log_path, report=report,
                      extra_select=extra_select, on_extra=on_extra,
                      autostart=autostart)
    app.run()
    return app.all_ok


def _demo_tasks():
    def slow(name, ok=True):
        def fn():
            time.sleep(0.5)
            if not ok:
                return False, "%s 失败：连接超时" % name
            return True, "%s 完成" % name
        return fn

    return [("连接设备", slow("连接设备")),
            ("上传升级包", slow("上传升级包")),
            ("安装", slow("安装", ok=False)),
            ("核对版本", slow("核对版本"))]


if __name__ == "__main__":
    if os.name == "nt" and not enable_vt():
        print("[XX] 需要 VT 终端（Windows Terminal / Win10+）")
        raise SystemExit(1)
    ok = run_tasks("app_showcase 演示", _demo_tasks(),
                   meta={"设备": "10.0.0.11", "说明": "这是内置演示数据"})
    print("结果：", "全部成功" if ok else "有失败")
