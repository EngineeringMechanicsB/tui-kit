---
name: tui-builder
description: >-
  Use when writing or reviewing a Windows command-line tool: coloured output, tables,
  progress bars, interactive menus, full-screen TUI, config files, auto mode, logs,
  test reports, or packaging a Python script into a Win7-compatible single-file exe.
  Trigger on: "写个脚本", "命令行界面", "TUI", "rich", "textual", "进度条", "彩色输出",
  "交互菜单", "配置文件", "自动模式", "测试报告", "打包 exe", "PyInstaller", "Win7",
  "单文件", "给生产部门用", "控制台乱码", "颜色不对". Also use when a CLI script is hard
  to configure on-site or has no logs/reports. Do NOT use for web UIs, desktop GUIs
  (tkinter/Qt), or non-Windows targets.
allowed-tools: Bash Read Write Edit Glob Grep
---

# Windows CLI/TUI 构建

目标：**Win10/11 好看好用，Win7 能清晰跑完，最后能打成单文件 exe。**

## 30 秒起步

把这三个文件复制进项目（都在 `assets/`）：

```python
# app.py
from config_kit import Config
from report_kit import Reporter
from ui_kit import UI

DEFAULTS = {"host": "10.0.0.11", "steps": ["check", "apply"]}
DOCS = {"host": "设备 IP", "steps": "默认执行哪些步骤"}

cfg = Config("mytool", DEFAULTS, DOCS).load()   # 首次运行生成配置
ui = UI()
ui.banner("mytool", cfg["host"])
ui.run_steps([("检查", do_check), ("应用", do_apply)])
ui.summary(1, 0, 0)
```

需要报告/日志再加 `report_kit`；需要全屏再加 `app_showcase`。
完整可跑样例：`examples/rich-cli/`、`examples/textual-app/`。

## 工作流（按顺序做，别跳步）

1. **定路线** —— 看下面表格。目标含 Win7 就只能 rich。
2. **搭骨架** —— 复制 `assets/` 组件，或直接用 `examples/` 里最接近的样例。
3. **写业务** —— 每个步骤是 `(名称, 回调)`；回调返回 `(ok, detail)`，**不 print**。
4. **补外围** —— 配置项、`--auto`、`--steps`、`--dry-run`、日志、报告。
5. **自检** —— `python scripts/check_script.py app.py`，再跑离线自测。
6. **打包**（需要时）—— `assets/build_win7.py`，打完必须验证 UCRT。

第 5 步不合格就不要交付：终端兼容问题在开发机看不出来，到产线才炸。

## 路线选择

| 需求 | 用什么 | Win7 |
|---|---|---|
| 彩色日志 / 表格 / 进度 / 步骤状态 | **rich**（默认） | ✅ |
| 编号菜单 + 回车确认 | rich + `input()` | ✅ |
| 按钮 / 键盘导航 / 标签页 / 鼠标 | **textual** | ❌ 要 py≥3.9 + VT |
| 什么都不想装 | 纯文本兜底 | ✅ |

判定：目标机有 Win7 → rich，不引入 textual。只在 Win10/11 全屏 → textual。
拿不准 → 先写 rich，95% 的运维脚本属于这一档。理由见 `references/decision.md`。

## 交付标准（缺一项都算没做完）

- [ ] 所有可变参数进配置文件；代码里没有硬编码 IP/密码/路径
- [ ] 首次运行自动生成带注释配置；坏配置先备份再重建
- [ ] `--auto` 不读输入；`--steps` 可选步骤；`--dry-run` 不连设备
- [ ] 失败退出码非 0；每步失败带原因
- [ ] 每次运行有日志；需要时生成 md/html/json 报告
- [ ] 状态同时用颜色 + ASCII 标记（`[OK] [XX] [!!] [i] [--]`）
- [ ] 自带离线自测（不连设备也能验证配置/退出码/报告）
- [ ] 跑过 `check_script.py`，没有 E 级问题

## 十条硬规则

1. **进场先开 VT**：`enable_vt()`。Win10/11 conhost 默认关闭，不开只有 16 色；
   开启后必须回读确认，Win7 上调用会假成功。
2. **Console 宽度减 1**：写满最后一列自动换行，Live 每帧下漂一行。`make_console()` 已处理。
3. **不用 `blue`**：老控制台 blue = `#000080`，黑底不可读。蓝色系用 `cyan`。
4. **不用 `dim`**：老控制台直接清亮度位。用 `bright_black`。
5. **标记用 ASCII**：`[OK] [XX] [!!] [i] [--]`，无 emoji、无方框字符。
6. **中文按 2 列**：手写对齐用东亚宽度；rich/textual 内部已处理。
7. **只在非 tty 改编码**：tty 下 Windows 用 `WriteConsoleW`，改了反而坏。
8. **交互只用 `input()`**：不要 readchar/msvcrt 方向键，输入法下极不稳。
9. **textual 自适应用轮询**：`set_interval(0.4, sync)` 读 `self.size`；
   Windows conpty 下 Resize 事件不可靠。
10. **Win7 只用 Python 3.8.10 打包**：3.9+ 依赖 Win8 专属 API。

为什么：`references/win7.md`。

## 组件速查

| 文件 | 什么时候用 |
|---|---|
| `assets/tui_boot.py` | 所有脚本的启动层：VT/主题/宽度/纯文本兜底 |
| `assets/ui_kit.py` | rich 界面：菜单、表格、`run_steps`、汇总、日志 tee |
| `assets/config_kit.py` | 配置：首次生成、缺项回填、坏文件备份 |
| `assets/report_kit.py` | 日志 + Markdown/HTML/JSON 报告 |
| `assets/app_showcase.py` | 全屏执行器（成品）：传步骤列表即可 |
| `assets/app_skeleton.py` | 全屏骨架：要自己设计界面时改它 |
| `assets/build_win7.py` | 打包 x64+x86，自动验 UCRT |
| `assets/templates/script_template.py` | 完整起步模板（配置+自动+报告） |
| `scripts/check_script.py` | 静态体检：ANSI/emoji/Live/编码/硬编码 |

`run_tasks(title, tasks, meta=..., report=..., extra_select=...)`
支持加一个下拉框（如选版本/升级包）。

## 验证（每次改完都做）

```bash
python scripts/check_script.py app.py        # 静态规则
python selftest.py                           # 离线自测：dry-run/退出码/报告/坏配置
python app.py --dry-run                      # 人工看计划
```

全屏界面用 headless 测，不用真终端：

```python
async with app.run_test(size=(120, 34)) as pilot:
    await pilot.pause(); app.action_start()
    await pilot.pause(1.0)
    await pilot.resize_terminal(70, 30); await pilot.pause(0.6)
    assert app.screen.has_class("narrow")
```

最后在**真终端**跑一次：Win10/11 看颜色与重绘，Win7（或 `--no-vt`）看是否只剩文字。

## 打包速查

```bash
python assets/build_win7.py --entry app.py --name mytool \
    --python-x64 D:\python38-x64\python.exe \
    --python-x86 D:\python38-x86\python.exe
python assets/build_win7.py --check dist\mytool-x64.exe
```

三件套 + 一件：Python 3.8.10、PyInstaller 5.13.2、setuptools<81、
**UCRT downlevel 显式打包**。细节与报错表：`references/packaging.md`。

## 参考文档

| 文件 | 内容 |
|---|---|
| `references/decision.md` | rich / textual / 纯文本怎么选，实测成本 |
| `references/rich-patterns.md` | rich 组件配方与常见错误 |
| `references/textual-patterns.md` | textual 骨架、CSS、事件、响应式、测试 |
| `references/config-and-automation.md` | 配置 / 自动模式 / 报告完整规范 |
| `references/win7.md` | Win7 运行时兼容全表 |
| `references/packaging.md` | 打包全流程、spec、UCRT、排错 |
| `references/checklist.md` | 交付前检查清单 |
| `references/sources.md` | 资料来源与取舍 |

## 反模式

- ❌ 为"好看"把 textual 带到 Win7 机器
- ❌ 手写 ANSI（`\033[32m`）却不做老控制台翻译
- ❌ 在 Live/Progress 里 `print()`
- ❌ 用 `str.ljust()` 对齐中文
- ❌ 参数写死在代码里，现场改一次就重新打包
- ❌ `--auto` 还弹确认框；失败仍 `exit 0`
- ❌ PyInstaller 6.x 打 Win7 包；依赖它自动收集 UCRT
- ❌ 用方向键菜单，现场输入法卡死

## 本机参考实现

| 参考 | 位置 | 学什么 |
|---|---|---|
| 设备配置主脚本 | `Desktop\AI\wtoe-device-config\run_all.py` | 菜单、参数默认值、分段开关、退出码 |
| 牌识升级 | `Desktop\AI\pai-shi-upgrade-cli-20261023\` | 配置/自动/报告/TUI/离线自测的完整落地 |
| ECN 测试台（Win7） | `Desktop\AI\ECN-测试台自动化_win7_20261016\` | 老控制台层、串口菜单 |
| 打包范例 | `...\build\x64\*.spec` | UCRT 显式打包 |

方法论：`Documents\Obsidian\zxw_obsidian\ai\设备网页逆向-自动化-打包经验.md`
