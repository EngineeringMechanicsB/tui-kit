---
name: tui-builder
description: >-
  写 Windows 命令行工具时用：彩色输出、进度条、表格、交互菜单、全屏 TUI，
  以及打包成 Win7 可用的单文件 exe。触发词："写个脚本"、"命令行界面"、"TUI"、
  "rich"、"textual"、"进度条"、"彩色输出"、"打包 exe"、"Win7"、"PyInstaller"、
  "单文件"、"给生产部门用"。也用于审查已有脚本的终端体验或打包配置。
allowed-tools: Bash Read Write Edit Glob Grep
---

# TUI 脚本构建规范

目标：**Win10/11 上尽可能好看好用，Win7 上只要能清晰跑完**。
一句话选型：**默认 rich；要全屏交互才上 textual；两样都没有就纯文本兜底。**

## 0. 先选路线（不要跳过）

| 需求 | 用什么 | 能不能 Win7 |
|---|---|---|
| 彩色日志 / 表格 / 进度 / 步骤状态 | **rich** | ✅ Python 3.8 + rich 14.0.0 |
| 编号菜单 + 回车确认 | **rich + input()** | ✅ |
| 键盘导航、按钮、标签页、实时刷新 | **textual** | ❌ 需要 VT + Python ≥3.9 |
| 机器上没装任何第三方库 | 纯文本（本插件的 fallback） | ✅ |

判定顺序：
1. 目标机含 Win7 → 只能 rich，**不要**引入 textual。
2. 只 Win10/11 且需要按钮/焦点/鼠标 → textual（`assets/app_skeleton.py`）。
3. 拿不准 → 先写 rich 版，`run_all.py` 这类运维脚本 95% 属于这一档。

详细对比与理由：`references/decision.md`。

## 1. 起步：复制三个文件

```
assets/tui_boot.py     # VT 探测 + 主题 + 宽度修正 + 纯文本兜底（约 150 行）
assets/ui_kit.py       # 菜单 / 表格 / run_steps / 汇总卡片
assets/templates/script_template.py   # 完整起步脚本，改 TODO 即可
```

最小用法：

```python
from ui_kit import UI

ui = UI()
ui.banner("设备批量配置", "10.0.0.11 · 3 个任务")
choice = ui.menu(["开始配置", "查看现状", "退出"])
results = ui.run_steps([("改密码", do_pwd), ("恢复出厂", do_reset)])
ui.summary(sum(1 for _, ok, _ in results if ok), sum(1 for _, ok, _ in results if not ok))
```

`run_steps` 的回调约定：返回 `True` / `(True, "说明")` / `"说明"` 算成功，
`False` / `(False, "说明")` / 抛异常算失败，异常文本自动进"说明"列。
**不要**在回调里自己 print，会打乱实时表格。

全屏版：`assets/app_skeleton.py`，三个 TODO 换成自己的业务。

## 2. 十条硬规则（全是实机踩出来的）

1. **进程序先开 VT**：`tui_boot.enable_vt()`。Win10/11 的 conhost 默认关着，
   不打开 rich 就退回 16 色。开启后必须**回读**确认，Win7 上调用会假成功。
2. **Console 宽度减 1**：写满最后一列会自动换行，Live 每帧往下漂一行。
   `tui_boot.make_console()` 已处理，自己建 Console 时别忘了。
3. **禁用 `blue`**：老控制台 blue = `#000080`，黑底看不见。蓝色系一律用 `cyan`。
4. **禁用 `dim`**：老控制台直接清亮度位，等于把颜色弄没。用 `bright_black`。
5. **标记用 ASCII**：`[OK] [XX] [!!] [i] [--]`，不要 emoji。
6. **中文宽度按 2 列算**：手写对齐用 `unicodedata.east_asian_width`，
   rich/textual 内部已处理，只有纯文本兜底需要自己算。
7. **非 tty 才改编码**：`sys.stdout.reconfigure(encoding="utf-8")` 只在管道下做，
   tty 下 Windows 用 `WriteConsoleW`，改了反而坏。
8. **交互只用 `input()`**：不要引 readchar/msvcrt 做方向键菜单——
   Win7 老控制台 + 中文输入法下极不稳，收益也低。
9. **textual 不要用 Resize 事件做自适应**：Windows conpty 下拖动/最大化不触发，
   用 `set_interval(0.4, sync_layout)` 轮询 `self.size.width`。
10. **Win7 只用 Python 3.8.10 打包**：3.9+ 的 `python39.dll` 依赖
    `api-ms-win-core-path-l1-1-0.dll`，Win7 补不上。

完整解释见 `references/win7.md`。

## 3. 组件速查

rich 版（`references/rich-patterns.md`）：
- 标题卡 / 分区线 / 结果卡 → `ui.banner` `ui.section` `ui.summary`
- 步骤实时表 + 总进度 → `ui.run_steps`
- 表格 → `ui.table`
- 转圈 → `ui.spinner("正在连接")`
- 确认 / 提问 → `ui.confirm` `ui.ask`
- 静态富文本（Markdown / 语法高亮 / 树）→ 直接用 rich 的
  `Markdown` `Syntax` `Tree` 包进 `Panel`

textual 版（`references/textual-patterns.md`）：
- 骨架 → `assets/app_skeleton.py`
- 表格 / 日志 / 统计卡 / 主题切换 / 模态确认 / 筛选 / 自适应都在里面

## 4. 打包成 Win7 单文件

```bash
python assets/build_win7.py --entry run_all.py --name wtoe-config
# 指定解释器：
python assets/build_win7.py --entry run_all.py --name wtoe-config \
    --python-x64 "D:\python38-x64\python.exe" \
    --python-x86 "D:\python38-x86\python.exe"
# 只验已有包：
python assets/build_win7.py --check dist\wtoe-config-x64.exe
```

脚本会自动：校验 3.8.x → 校验 PyInstaller 5.13.2 + setuptools<81 →
生成 spec（把 `System32\downlevel` / `SysWOW64\downlevel` 的 UCRT 显式打进包）→
打包 → 用 `archive_viewer` 验证 `ucrtbase.dll` 在里面。

**只在本机装一次环境**：

```bat
pip install "rich==14.0.0"
pip install "pyinstaller==5.13.2" "setuptools<81"
```

细节、spec 全文、常见报错：`references/packaging.md`。

## 5. 交付前清单

`references/checklist.md`。至少确认：

- [ ] Win10/11 真终端里跑一遍：颜色、对齐、进度不跳行
- [ ] `--no-color` / 管道输出没有乱码、没有 ANSI 残留
- [ ] 出错路径有明确提示（不要静默失败）
- [ ] exe 用 `--check` 验证过 `ucrtbase.dll`
- [ ] 目标机是 32 位就打了 x86

## 6. 参考文档

| 文件 | 内容 |
|---|---|
| `references/decision.md` | rich / textual / 纯文本怎么选，成本对比 |
| `references/rich-patterns.md` | 常用 rich 组件代码配方 |
| `references/textual-patterns.md` | textual 骨架、CSS、响应式、测试 |
| `references/win7.md` | Win7 运行时兼容全表（VT、配色、emoji、编码） |
| `references/packaging.md` | 打包全流程、spec、UCRT、排错 |
| `references/checklist.md` | 交付前检查清单 |
| `references/sources.md` | 资料来源、实测结论、取舍 |

## 7. 反模式

- ❌ 为了"好看"引入 textual 到 Win7 机器
- ❌ 用 ANSI 手写颜色（`\033[32m`）却不做老控制台翻译
- ❌ 在 Live/Progress 里 `print()`
- ❌ 表格用 `str.ljust()` 对齐中文
- ❌ PyInstaller 6.x 打 Win7 包
- ❌ 依赖 PyInstaller 自动收集 UCRT
- ❌ 把 `input()` 换成方向键菜单，结果现场输入法卡死

## 8. 本机现成参考实现

写新脚本前先看这几个（路径固定，直接 Read）：

| 参考 | 位置 | 学什么 |
|---|---|---|
| 设备配置主脚本 | `Desktop\AI\wtoe-device-config\run_all.py` | 交互菜单、参数默认值、分段开关、退出码 |
| 摄像头口令改写 | `...\cam_password.py` | 板子侧脚本下发、按字段改写、回读校验 |
| 海康 ISAPI | `...\hk_config.py` | 并发、重试、候选密码 |
| ECN 测试台（Win7） | `Desktop\AI\ECN-测试台自动化_win7_20261016` | `win_console.py` 老控制台层、串口菜单 |
| 打包范例 | `...\build\x64\*.spec` | UCRT 显式打包 |

共同约定（保持一致）：

- 退出码：0 成功，非 0 失败（批量脚本据此统计）
- 标记：`[OK] [XX] [!!] [i] [--]`
- 每个步骤失败要带原因，不静默跳过
- 默认值写进 argparse，交互菜单和命令行共用
- 中文注释

方法论笔记（Obsidian）：
`Documents\Obsidian\zxw_obsidian\ai\设备网页逆向-自动化-打包经验.md`
（第三节是 Win7 打包的完整来龙去脉）
