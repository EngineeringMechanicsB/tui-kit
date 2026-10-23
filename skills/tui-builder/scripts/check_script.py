#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_script.py —— 静态检查一个 Python 脚本是否符合 tui-kit 规范

用法：
    python check_script.py app.py
    python check_script.py app.py --json
    python check_script.py src/            # 目录下所有 .py

只查"能确定"的问题，不猜业务。退出码：0 无问题，1 有 error，2 参数错误。

检查项：
  E1  裸 ANSI 转义（\\033[ / \\x1b[）        老控制台会打出 ←[32m
  E2  使用了 blue / dim 样式                 老控制台不可读
  E3  emoji 字符                             老控制台无字形
  W1  导入 rich/textual 但没调用 enable_vt()  Win10 下会掉到 16 色
  W2  sys.stdout.reconfigure 没有 isatty 保护  tty 下改编码会坏
  W3  Live/Progress 块里有 print()            会打乱重绘
  W4  中文用 str.ljust/rjust 手写对齐         中文按 1 列算，必错位
  I1  有 argparse 但没有 --dry-run / --help 之外的预演开关
  I2  疑似硬编码 IP / 密码
"""
import argparse
import ast
import io
import json
import os
import re
import sys

EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]")
ANSI = re.compile(r"(\\033\[|\\x1b\[|\x1b\[)")
BAD_STYLE = re.compile(r"""["'\[][^"'\]\n]*\b(blue|dim)\b[^"'\]\n]*["'\]]""")
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PASSWORD = re.compile(r"""(?i)(password|passwd|pwd)\s*[:=]\s*["'][^"']{3,}["']""")


def scan(path):
    """返回 [(级别, 行号, 说明)]"""
    try:
        text = io.open(path, encoding="utf-8", errors="replace").read()
    except Exception as e:
        return [("E", 0, "无法读取：%s" % e)]
    lines = text.splitlines()
    findings = []

    # E1 裸 ANSI
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith("#"):
            continue
        if ANSI.search(line) and "win_console" not in path and "tui_boot" not in path:
            findings.append(("E", i, "裸 ANSI 转义；用 rich 主题名或 tui_boot 的翻译层"))
            break

    # E2 blue / dim
    for i, line in enumerate(lines, 1):
        if '"blue"' in line or "'blue'" in line or '"dim"' in line or "'dim'" in line:
            if "禁用" in line or "不要" in line or "#" in line.split("blue")[0][-2:]:
                continue
            findings.append(("E", i, "样式里出现 blue/dim；老控制台不可读，改用 cyan/bright_black"))
            break

    # E3 emoji
    for i, line in enumerate(lines, 1):
        if EMOJI.search(line):
            findings.append(("E", i, "含 emoji：%r；改用 [OK]/[XX] 这类 ASCII 标记"
                            % EMOJI.search(line).group(0)))
            break

    # W1 有 rich 但没 enable_vt
    if ("import rich" in text or "from rich" in text or "import textual" in text):
        if "enable_vt" not in text and "make_console" not in text:
            findings.append(("W", 0, "导入 rich/textual 但没调用 enable_vt()；先看看终端适配"))

    # W2 reconfigure 无保护
    for i, line in enumerate(lines, 1):
        if "reconfigure(" in line and "isatty" not in line:
            prev = "\n".join(lines[max(0, i - 4):i])
            if "isatty" not in prev:
                findings.append(("W", i, "reconfigure 没有 isatty 保护；只有非 tty 才应改编码"))
                break

    # W3 Live 里有 print
    in_live = False
    live_indent = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if re.search(r"\bwith\s+Live\(", line):
            in_live, live_indent = True, indent
            continue
        if in_live:
            if stripped and indent <= live_indent and not stripped.startswith("#"):
                in_live = False
            elif "print(" in stripped and not stripped.startswith("#"):
                findings.append(("W", i, "Live/Progress 块里有 print()；会破坏重绘"))
                in_live = False

    # W4 中文 ljust
    for i, line in enumerate(lines, 1):
        if re.search(r"\.(ljust|rjust)\(", line):
            snippet = "\n".join(lines[max(0, i - 3):i + 3])
            if re.search("[一-鿿]", snippet):
                findings.append(("W", i, "中文附近用了 ljust/rjust；按 2 列算宽度或用 rich 表格"))
                break

    # I1 无 dry-run
    if "argparse" in text and "--dry-run" not in text:
        findings.append(("I", 0, "argparse 里没有 --dry-run；建议加，现场排查先看计划"))

    # I2 硬编码 IP / 密码
    try:
        tree = ast.parse(text)
        literals = [n.value for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    except SyntaxError:
        literals = []
    ips = sorted({s for s in literals if IPV4.fullmatch(s) and not s.startswith("127.")})
    if ips:
        findings.append(("I", 0, "代码里有硬编码 IP：%s；建议放进配置文件" % ", ".join(ips[:3])))
    if PASSWORD.search(text):
        findings.append(("I", 0, "疑似硬编码密码；放进配置文件，别提交进仓库"))

    return findings


def main():
    ap = argparse.ArgumentParser(description="按 tui-kit 规范静态检查脚本")
    ap.add_argument("path", help="文件或目录")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    if os.path.isdir(args.path):
        files = []
        for root, _, names in os.walk(args.path):
            for n in names:
                if n.endswith(".py") and not n.startswith("_"):
                    files.append(os.path.join(root, n))
    elif os.path.isfile(args.path):
        files = [args.path]
    else:
        print("路径不存在：%s" % args.path)
        return 2

    report = {}
    errors = 0
    for f in files:
        found = scan(f)
        if found:
            report[f] = [{"level": lv, "line": ln, "message": msg} for lv, ln, msg in found]
            errors += sum(1 for lv, _, _ in found if lv == "E")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if not report:
            print("[OK] %d 个文件，没有发现问题" % len(files))
        for f, items in report.items():
            print("\n%s" % f)
            for it in items:
                mark = {"E": "[XX]", "W": "[!!]", "I": "[i]"}[it["level"]]
                where = ":%d" % it["line"] if it["line"] else ""
                print("  %s%s %s" % (mark, where, it["message"]))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
