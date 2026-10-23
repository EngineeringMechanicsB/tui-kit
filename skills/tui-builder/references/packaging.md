# 打包成 Win7 单文件 exe

## 0. 三条硬性约束

| 约束 | 值 | 违反后果 |
|---|---|---|
| Python | **3.8.10** | 3.9+ 的 `python39.dll` 依赖 `api-ms-win-core-path-l1-1-0.dll`（Win8 才有），Win7 报缺 DLL |
| PyInstaller | **5.13.2** | 6.x bootloader 用新 VS 编，可能引入 Win8 API |
| setuptools | **<81** | 81 起移除 `pkg_resources`，PyInstaller 5.x 直接 `ModuleNotFoundError` |

外加第四件：**UCRT 必须显式打进包**（见第 3 节）。

## 1. 一次性环境

```bat
:: 64 位
python-3.8.10-amd64.exe /quiet InstallAllUsers=0 TargetDir=D:\python38-x64 Include_pip=1 PrependPath=0 Include_launcher=0
:: 32 位
python-3.8.10.exe /quiet InstallAllUsers=0 TargetDir=D:\python38-x86 Include_pip=1 PrependPath=0 Include_launcher=0
```

安装包地址：
`https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe` / `python-3.8.10.exe`

```bat
D:\python38-x64\python.exe -m pip install --upgrade "pip<25"
D:\python38-x64\python.exe -m pip install "rich==14.0.0" "pyinstaller==5.13.2" "setuptools<81"
```

x86 同理。**交叉编译不存在**：32 位 exe 必须用 32 位 Python 打。

> 已有一份可复用的环境：`Desktop\AI\camera-ip-setter\python38-x64\` 和 `python38-x86\`。

## 2. 打包命令

用插件自带的脚本（推荐）：

```bash
python skills/tui-builder/assets/build_win7.py \
    --entry run_all.py --name wtoe-config \
    --python-x64 D:\python38-x64\python.exe \
    --python-x86 D:\python38-x86\python.exe
```

它会依次校验解释器/依赖 → 生成 spec → 打包 → 验 UCRT。

手工等价命令：

```bat
D:\python38-x64\python.exe -m PyInstaller --noconfirm --clean ^
    --distpath dist --workpath build\x64 build\x64\wtoe-config-x64.spec
D:\python38-x86\python.exe -m PyInstaller --noconfirm --clean ^
    --distpath dist --workpath build\x86 build\x86\wtoe-config-x86.spec
```

`--workpath` 分开，避免两个架构互相覆盖。

## 3. spec：UCRT 必须显式打进去

PyInstaller 自动收集 UCRT **不可靠**：实测 x64 只收到 `api-ms-win-crt-*`，
漏掉 `ucrtbase.dll` 和 39 个 `api-ms-win-core-*`；x86 一个都不收。
目标机没装 VC++ 2015+ 运行库就报缺 DLL。

正确做法是取微软的 downlevel 目录：

```python
import os
DOWNLEVEL = r"C:\Windows\System32\downlevel"          # x86 用 C:\Windows\SysWOW64\downlevel
UCRT = [(os.path.join(DOWNLEVEL, f), ".")
        for f in sorted(os.listdir(DOWNLEVEL)) if f.lower().endswith(".dll")]

a = Analysis(['run_all.py'], binaries=UCRT, ...)
```

为什么这份能用在 Win7：它的 `ucrtbase.dll` 只导入 Win7 自带的
`api-ms-win-core-*`，不含 Win8 专属的 `api-ms-win-core-path-*`。

完整 spec（由 `build_win7.py` 生成，可直接抄）：

```python
# -*- mode: python ; coding: utf-8 -*-
import os

DOWNLEVEL = r"C:\Windows\System32\downlevel"
UCRT = [(os.path.join(DOWNLEVEL, name), ".")
        for name in sorted(os.listdir(DOWNLEVEL)) if name.lower().endswith(".dll")]

a = Analysis(
    [r"D:\proj\run_all.py"],
    pathex=[r"D:\proj"],
    binaries=UCRT,
    datas=[("netplan_template.txt", ".")],
    hiddenimports=["serial", "serial.tools.list_ports"],
    excludes=["tkinter", "numpy", "pandas", "matplotlib", "PyQt5", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
          name="wtoe-config-x64", debug=False, strip=False, upx=False, console=True)
```

注意：
- 没有 `COLLECT` = onefile
- `upx=False`：UPX 压缩容易被杀软误报，体积也没小多少
- `excludes` 排掉 tkinter/numpy 等，能省 10–20 MB
- 数据文件用 `datas`，运行时从 `sys._MEIPASS` 取

## 4. 打完必须自查

```bat
python -m PyInstaller.utils.cliutils.archive_viewer -l dist\wtoe-config-x64.exe | findstr ucrtbase
```

输出行里第 3 个数字是**解压后大小**，必须等于：

| 架构 | ucrtbase.dll 解压后 |
|---|---|
| x64 | 1044880 |
| x86 | 1181200 |

（不同 Windows 版本略有差异，以本机 `downlevel\ucrtbase.dll` 的实际大小为准。）

也可以查导入表确认没有 Win8 API：

```python
import pefile
pe = pefile.PE('dist/app-x64.exe')
dlls = {e.dll.decode() for e in pe.DIRECTORY_ENTRY_IMPORT}
print('有 path API:', any('api-ms-win-core-path' in d for d in dlls))   # 应为 False
```

`build_win7.py --check dist\app-x64.exe` 就是做第一件事。

## 5. 体积参考

| 内容 | x64 | x86 |
|---|---|---|
| 纯标准库 | ~7 MB | ~6.5 MB |
| + rich（本插件实测） | 9.2 MB | 8.6 MB |
| + requests + paramiko + cryptography | ~18–20 MB | ~17–19 MB |
| + textual | ~21–25 MB | 不适用（Win7 不支持） |
| 加 `--upx` | 通常省 20%，但杀软误报↑ |

## 6. 常见报错

| 现象 | 原因 | 修法 |
|---|---|---|
| Win7 提示缺 `api-ms-win-core-path-l1-1-0.dll` | 用 3.9+ 打的 | 换 Python 3.8.10 |
| Win7 提示缺 `VCRUNTIME140.dll` / `ucrtbase.dll` | UCRT 没打进包 | spec 里加 downlevel（第 3 节） |
| `ModuleNotFoundError: pkg_resources` | setuptools ≥81 | `pip install "setuptools<81"` |
| exe 启动闪退，无输出 | 未捕获异常 | 先 `--console` 从 cmd 运行看堆栈 |
| 32 位 exe 在 64 位机报错 | 打反了架构 | 确认 x86 用 32 位 Python |
| 杀软拦截 | onefile 自解压行为敏感 | 加白名单 / 用 onedir / 代码签名 |
| 启动慢 2 秒 | onefile 每次解压 | 可接受；或改 onedir |
| 中文路径下崩溃 | 老 3.8 对非 ASCII 路径处理 | 路径统一英文，或 `os.fsencode` |

## 7. 数据文件与隐藏依赖

```python
# spec
datas=[("config/default.ini", "."), ("assets", "assets")],
hiddenimports=["serial", "serial.tools.list_ports", "cryptography.hazmat.backends.openssl"],
```

运行时定位：

```python
import sys, os
BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(BASE, "default.ini")
```

`paramiko` / `cryptography` / `serial` 经常需要 hiddenimports，漏了表现为
"源码跑得好，打包后 ImportError"。

## 8. 版本信息与图标（可选）

```bat
pyinstaller --icon app.ico --version-file version.txt ...
```

`version.txt` 用 PyInstaller 的 VSVersionInfo 格式，能在 exe 属性里显示版本/公司。
给生产部门的工具建议加，方便确认是不是最新版。

## 9. 测试与交付

1. **本机**：`dist\app-x64.exe --help` + 一条真实命令
2. **`--check`**：确认 ucrtbase 在包里
3. **Win7 虚拟机**（裸系统，不装 VC++）：双击、跑完整流程
4. 32 位机器单独测 x86 包
5. 交付时给两个 exe + 一行说明（哪个系统用哪个）

## 10. 重打包检查表

源码改了以后：

- [ ] 重新打包（不要发旧的 exe）
- [ ] `--check` 过了
- [ ] 版本号 +1（如果加了 version 资源）
- [ ] 新增第三方依赖 → 确认 hiddenimports / datas
- [ ] 新增数据文件 → 确认 datas + `_MEIPASS` 读取
- [ ] x64/x86 都重打
