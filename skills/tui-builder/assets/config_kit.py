#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config_kit.py —— 带注释的配置文件（首次运行自动生成）

解决的问题：
  - 参数一多，命令行记不住 → 全部落进配置文件，命令行只做覆盖
  - 配置文件要能直接给人看 → 每项上面一行中文注释，仍然是合法 JSON（JSONC）
  - 升级脚本后新增参数 → 老配置缺的键自动补上并写回，用户不用手动加
  - 用户手改出语法错 → 备份成 .bad-时间戳，再用默认值恢复，不直接盖掉

用法：
    from config_kit import Config

    DEFAULTS = {"host": "10.0.0.11", "port": 22, "timeout": 30}
    DOCS = {"host": "设备 IP", "port": "SSH 端口", "timeout": "单条命令超时（秒）"}

    cfg = Config("我的工具", DEFAULTS, DOCS)   # 首次运行生成 <脚本目录>/我的工具_config.json
    cfg.load()
    host = cfg["host"]
    cfg["host"] = "10.0.0.12"; cfg.save()

    # 命令行覆盖：
    ap.add_argument("--host", default=cfg["host"])
    ...
    cfg.update_from_args(args)   # 可选：把 args 里同名项写回

兼容 Python 3.8 / Win7。
"""
import json
import os
import shutil
import sys
import time

__all__ = ["Config", "strip_comments", "default_dir"]


def default_dir(app_name):
    """配置放哪：优先脚本所在目录（便携），没有写权限时退回用户目录"""
    base = os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv and sys.argv[0] else os.getcwd()
    try:
        probe = os.path.join(base, ".write_test")
        with open(probe, "w") as f:
            f.write("1")
        os.remove(probe)
        return base
    except Exception:
        return os.path.join(os.path.expanduser("~"), app_name)


def strip_comments(text):
    """去掉 // 注释，保留字符串里的 //（路径、URL 不会被误伤）"""
    out = []
    for line in text.splitlines():
        res, in_str, esc = [], False, False
        i = 0
        while i < len(line):
            c = line[i]
            if in_str:
                res.append(c)
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
                res.append(c)
            elif c == "/" and i + 1 < len(line) and line[i + 1] == "/":
                break
            else:
                res.append(c)
            i += 1
        out.append("".join(res))
    return "\n".join(out)


class Config(object):
    def __init__(self, app_name, defaults, docs=None, path=None, out_dir=None):
        self.app_name = app_name
        self.defaults = dict(defaults)
        self.docs = docs or {}
        self.dir = out_dir or default_dir(app_name)
        self.path = path or os.path.join(self.dir, "%s_config.json" % app_name)
        self.data = dict(defaults)
        self.loaded_from_disk = False

    # ------------------------------------------------------------ 读写
    def load(self, quiet=False):
        """读配置；文件不存在就生成一份（带注释）"""
        existed = os.path.exists(self.path)
        file_keys = set()
        if existed:
            try:
                with open(self.path, "r", encoding="utf-8-sig") as f:
                    user = json.loads(strip_comments(f.read()))
                if isinstance(user, dict):
                    file_keys = set(user)
                    self.data.update({k: v for k, v in user.items() if not k.startswith("_")})
                    self.loaded_from_disk = True
            except Exception as e:
                # 用户手改坏了：先备份，再用默认值重建，绝不直接盖掉
                broken = "%s.bad-%s" % (self.path, time.strftime("%Y%m%d_%H%M%S"))
                try:
                    shutil.copyfile(self.path, broken)
                except Exception:
                    broken = "(备份失败)"
                if not quiet:
                    print("  [配置] 读取失败：%s" % e)
                    print("  [配置] 原文件已备份为 %s，将用默认值重建" % broken)
                existed = False

        missing = [k for k in self.defaults if k not in file_keys]
        if not existed or missing:
            self.save(quiet=quiet)
            if not quiet:
                print("  [配置] %s %s" % ("已生成" if not existed else "已补全新项", self.path))
        return self

    def save(self, quiet=False):
        d = os.path.dirname(self.path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        parts, known = [], set(self.docs)
        for key in self.defaults:
            doc = self.docs.get(key)
            block = []
            if doc:
                for line in (doc if isinstance(doc, (list, tuple)) else [doc]):
                    block.append("  // " + line)
            block.append('  "%s": %s' % (key, json.dumps(self.data.get(key, self.defaults[key]),
                                                        ensure_ascii=False)))
            parts.append("\n".join(block))
        rest = [k for k in self.data if k not in known]
        if rest:
            parts.append("  // ↓ 下面这些是脚本不认识的项（原样保留）")
            for k in rest:
                parts.append('  "%s": %s' % (k, json.dumps(self.data[k], ensure_ascii=False)))
        head = ("  // %s 配置文件 —— 改完保存即可，脚本每次运行都会读。\n"
                "  // 命令行参数优先于本文件；删掉某一项 = 用脚本内置默认值（下次运行自动补回）。\n"
                "  // 注释以 // 开头，可以独占一行，也可以写在值后面。\n"
                % self.app_name)
        text = "{\n" + head + "\n" + ",\n".join(parts) + "\n}\n"
        try:
            with open(self.path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            if not quiet:
                print("  [配置] 已写入 %s" % self.path)
        except Exception as e:
            print("  [配置] 写入 %s 失败：%s" % (self.path, e))
        return self

    # ------------------------------------------------------------ 访问
    def __getitem__(self, key):
        return self.data.get(key, self.defaults.get(key))

    def __setitem__(self, key, value):
        self.data[key] = value

    def get(self, key, default=None):
        return self.data.get(key, self.defaults.get(key, default))

    def as_dict(self):
        return dict(self.data)

    def update_from_args(self, args, keys=None):
        """把命令行里显式给出的值写回配置（用于 --save / 记忆上次参数）

        只认 argparse 里有同名的项；值为 None 的跳过。
        """
        namespace = vars(args)
        for key in (keys or self.defaults):
            if key in namespace and namespace[key] is not None:
                self.data[key] = namespace[key]
        return self

    def reload(self):
        self.data = dict(self.defaults)
        return self.load(quiet=True)


if __name__ == "__main__":
    DEFAULTS = {"host": "10.0.0.11", "port": 22, "timeout": 30,
                "steps": ["upload", "install"], "report": True}
    DOCS = {"host": "设备 IP，连不上时先 ping",
            "port": "SSH 端口",
            "timeout": "单条命令超时（秒）",
            "steps": "默认执行哪些步骤（上传/安装/重启/核对）",
            "report": "是否生成测试报告"}
    cfg = Config("config_kit_demo", DEFAULTS, DOCS, out_dir=".")
    cfg.load()
    print("读取到的配置：", cfg.as_dict())
    print("配置文件路径：", cfg.path)
