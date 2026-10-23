#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_win7.py —— 一键把 Python 脚本打成 Win7 可用的单文件 exe（x64 + x86）

它替你做四件事，每一步都是踩过的坑：
  1. 校验 Python 是不是 3.8.x（3.9+ 的 python39.dll 依赖 Win8 专属 API，Win7 必炸）
  2. 校验 PyInstaller 是不是 5.13.2、setuptools 是否 <81（否则 pkg_resources 缺失）
  3. 生成 spec：把 System32\\downlevel（x86 用 SysWOW64\\downlevel）的 112 个 UCRT DLL
     显式塞进 binaries —— PyInstaller 自动收集不可靠，裸 Win7 会报缺 DLL
  4. 打完自查：archive_viewer 里必须有 ucrtbase.dll，且解压尺寸与源文件一致

用法：
    python build_win7.py --entry run_all.py --name wtoe-config
    python build_win7.py --entry app.py --name tool --arch x64
    python build_win7.py --check dist/wtoe-config-x64.exe        # 只验已有 exe

Python 3.8 解释器位置（二选一）：
    --python-x64 "C:\\...\\python38-x64\\python.exe" --python-x86 "..."
    或设环境变量 PY38_X64 / PY38_X86

只在本机打当前架构也可以：--arch auto（默认用 sys.executable，但仍要求 3.8）。
"""
import argparse
import os
import re
import subprocess
import sys

SPEC_TEMPLATE = '''# -*- mode: python ; coding: utf-8 -*-
# 自动生成，勿手改：{source}
import os

DOWNLEVEL = r"{downlevel}"
UCRT = [
    (os.path.join(DOWNLEVEL, name), ".")
    for name in sorted(os.listdir(DOWNLEVEL))
    if name.lower().endswith(".dll")
]

a = Analysis(
    [r"{entry}"],
    pathex=[r"{entry_dir}"],
    binaries=UCRT,
    datas={datas},
    hiddenimports={hidden},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        "tkinter", "numpy", "pandas", "matplotlib", "scipy",
        "PyQt5", "PySide2", "PySide6", "IPython", "pytest",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="{name}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)
'''

EXPECTED = {
    "x64": r"C:\Windows\System32\downlevel",
    "x86": r"C:\Windows\SysWOW64\downlevel",
}


def run(cmd, **kw):
    print("$", " ".join(cmd) if isinstance(cmd, list) else cmd)
    return subprocess.call(cmd, **kw)


def check_python(python, arch):
    """返回 (版本字符串, 是否合格)"""
    try:
        out = subprocess.check_output(
            [python, "-c", "import sys;print('%d.%d.%d' % sys.version_info[:3])"],
            stderr=subprocess.STDOUT).decode().strip()
    except Exception as e:
        return "无法运行 %s: %s" % (python, e), False
    return out, out.startswith("3.8.")


def check_deps(python):
    """返回问题列表"""
    problems = []
    try:
        out = subprocess.check_output(
            [python, "-c",
             "import importlib.metadata as m;"
             "print(m.version('pyinstaller'));"
             "print(m.version('setuptools'))"],
            stderr=subprocess.STDOUT).decode().split()
    except Exception as e:
        return ["读依赖版本失败：%s" % e]
    pi = out[0] if out else "?"
    st = out[1] if len(out) > 1 else "?"
    if pi != "5.13.2":
        problems.append("PyInstaller 是 %s，Win7 需要 5.13.2" % pi)
    try:
        if int(st.split(".")[0]) >= 81:
            problems.append("setuptools 是 %s，>=81 移除了 pkg_resources，请装 setuptools<81" % st)
    except ValueError:
        pass
    return problems


def make_spec(entry, name, arch, dist_dir, hidden, datas):
    downlevel = EXPECTED[arch]
    if not os.path.isdir(downlevel):
        raise SystemExit("找不到 %s（这台机器没有对应架构的 downlevel 目录）" % downlevel)
    entry_dir = os.path.dirname(os.path.abspath(entry))
    spec_dir = os.path.join("build", arch)
    os.makedirs(spec_dir, exist_ok=True)
    exe_name = "%s-%s" % (name, arch)
    spec_path = os.path.join(spec_dir, "%s.spec" % exe_name)
    text = SPEC_TEMPLATE.format(
        source=os.path.abspath(__file__),
        downlevel=downlevel,
        entry=os.path.abspath(entry),
        entry_dir=entry_dir,
        datas=repr(datas),
        hidden=repr(hidden),
        name=exe_name,
    )
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("[i] spec: %s（UCRT 来自 %s）" % (spec_path, downlevel))
    return spec_path


def build(python, spec, arch, dist_dir):
    return run([python, "-m", "PyInstaller", "--noconfirm", "--clean",
                "--distpath", dist_dir, "--workpath", os.path.join("build", arch),
                spec])


def verify(exe, arch, python=None):
    """检查 ucrtbase 在包里的解压尺寸是否与源文件一致"""
    if not os.path.exists(exe):
        print("[XX] 找不到 %s" % exe)
        return False
    src = os.path.join(EXPECTED[arch], "ucrtbase.dll")
    want = os.path.getsize(src) if os.path.exists(src) else None
    try:
        out = subprocess.check_output(
            [python or sys.executable, "-m", "PyInstaller.utils.cliutils.archive_viewer",
             "-l", exe], stderr=subprocess.STDOUT).decode("utf-8", "replace")
    except Exception as e:
        print("[!!] 无法运行 archive_viewer：%s" % e)
        return False

    line = next((l for l in out.splitlines() if "ucrtbase.dll" in l), None)
    if not line:
        print("[XX] 包里没有 ucrtbase.dll —— 裸 Win7 会报缺 DLL")
        return False

    nums = [int(n) for n in re.findall(r"\d{5,}", line)]
    ok = want is None or want in nums
    size = os.path.getsize(exe) / 1024.0 / 1024.0
    print("%s %s  %.1f MB" % ("[OK]" if ok else "[!!]", exe, size))
    if want is not None and not ok:
        print("     ucrtbase 解压尺寸没对上（期望 %d，日志：%s）" % (want, line.strip()))
    return ok


def main():
    ap = argparse.ArgumentParser(description="打包成 Win7 单文件 exe")
    ap.add_argument("--entry", default=None, help="入口脚本，如 run_all.py")
    ap.add_argument("--name", default=None, help="exe 名字（不含架构后缀）")
    ap.add_argument("--arch", default="both", choices=["both", "x64", "x86", "auto"],
                    help="默认 both；auto = 只用当前解释器")
    ap.add_argument("--python-x64", default=os.environ.get("PY38_X64"))
    ap.add_argument("--python-x86", default=os.environ.get("PY38_X86"))
    ap.add_argument("--hidden", default="", help="额外 hiddenimports，逗号分隔")
    ap.add_argument("--datas", default="", help="额外数据文件，src;dest 逗号分隔")
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--check", default=None, help="只校验已有 exe")
    ap.add_argument("--skip-verify", action="store_true")
    args = ap.parse_args()

    if args.check:
        arch = "x86" if "x86" in os.path.basename(args.check).lower() else "x64"
        return 0 if verify(args.check, arch) else 1

    if not args.entry or not args.name:
        ap.error("需要 --entry 和 --name（或用 --check 验包）")
    if not os.path.exists(args.entry):
        ap.error("入口不存在：%s" % args.entry)

    hidden = [x.strip() for x in args.hidden.split(",") if x.strip()]
    datas = []
    for item in args.datas.split(","):
        if ";" in item:
            src, dst = item.split(";", 1)
            datas.append((src.strip(), dst.strip()))

    targets = []
    if args.arch == "auto":
        targets = [("x64" if sys.maxsize > 2 ** 32 else "x86", sys.executable)]
    else:
        if args.arch in ("both", "x64"):
            targets.append(("x64", args.python_x64))
        if args.arch in ("both", "x86"):
            targets.append(("x86", args.python_x86))

    for arch, python in targets:
        if not python:
            print("[!!] 跳过 %s：没提供 Python 3.8 解释器（--python-%s 或 PY38_%s）"
                  % (arch, arch, arch.upper()))
            continue
        ver, good = check_python(python, arch)
        print("\n=== %s  %s  Python %s ===" % (arch, python, ver))
        if not good:
            print("[XX] 必须用 Python 3.8.x：3.9+ 依赖 Win8 的 api-ms-win-core-path，Win7 跑不了")
            continue
        problems = check_deps(python)
        if problems:
            for p in problems:
                print("[XX] " + p)
            print('    修法："%s" -m pip install "pyinstaller==5.13.2" "setuptools<81"' % python)
            continue
        spec = make_spec(args.entry, args.name, arch, args.dist, hidden, datas)
        if build(python, spec, arch, args.dist) != 0:
            print("[XX] %s 打包失败" % arch)
            continue
        exe = os.path.join(args.dist, "%s-%s.exe" % (args.name, arch))
        if not args.skip_verify:
            verify(exe, arch, python)
    return 0


if __name__ == "__main__":
    sys.exit(main())
