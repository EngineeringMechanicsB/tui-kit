# 资料来源与取舍

写这个插件时参考了什么、哪些采纳、哪些没采纳。

## 官方文档

- Rich — https://rich.readthedocs.io/
  采纳：`Live` / `Progress` / `Table` / `Panel` / `Markdown` / `Syntax` / `Tree` 用法；
  确认 `rich/_win32_console.py` 自带老控制台渲染器。
- Textual — https://textual.textualize.io/
  采纳：`App` / `compose` / CSS / `DataTable` / `run_test` / `ModalScreen` / `theme`。
  未采纳：`on_resize` 做响应式（Windows conpty 下不触发，改轮询）。
- PyInstaller — https://pyinstaller.org/
  采纳：spec 结构、onefile、`archive_viewer` 校验。

## 已知问题（conhost / 中文）

- Textual issue #5456 — 日文输入在 conhost 下消失
  https://github.com/Textualize/textual/issues/5456
- Textual issue #4974 — Windows conhost 符号显示异常，维护者建议用 Windows Terminal
  https://github.com/Textualize/textual/issues/4974
- microsoft/terminal #10472 — conhost GDI 渲染器无缺字回退
  https://github.com/microsoft/terminal/issues/10472
- wtmux 4.0.0 发布说明 — conhost 按码点计算宽度，与现代终端按字素簇不同
  https://newreleases.io/project/github/fukuyori/wtmux/release/4.0.0

结论：Textual 的中文重绘问题来自 conhost 本身，代码层面只能"建议 Windows Terminal"，
不能修。插件里把它写成已知限制。

## Skill / 插件写法（调研对象）

- Anthropic 官方 `anthropics/skills` → `skill-creator/SKILL.md`
  https://github.com/anthropics/skills
  采纳：description 只写"何时用/何时不用"、正文 <500 行、资源分级加载、脚本承担确定性工作。
- Anthropic Agent Skills 规范
  https://mintlify.wiki/anthropics/skills/spec/overview
  采纳：三层渐进披露（元数据 / SKILL.md / 资源）、reference 只嵌套一层。
- obra/superpowers → `writing-skills`
  https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md
  采纳：先用真实任务验证 skill 会不会被触发；"如果没看它失败过，就不知道它教对了没"。
- hesreallyhim/awesome-claude-code
  https://github.com/hesreallyhim/awesome-claude-code
  参考：插件目录组织、常见组件（commands / agents / hooks）。

未采纳：多智能体编排、hooks 常驻注入。本插件是"写代码时查的规范"，
不需要在每次会话里注入内容，常驻 token 越少越好。

## Python CLI 模板（调研对象）

- sschleemilch/cookiecutter-python-cli — https://github.com/sschleemilch/cookiecutter-python-cli
- ltpitt/python-cookiecutter-typer-cli — https://github.com/ltpitt/python-cookiecutter-typer-cli

采纳思路：组件化、模板即文档、`assets/` 放可复制文件。
未采纳：cookiecutter / uv / typer 整套脚手架 —— 目标机器有 Win7，
多一层依赖和多一个打包变量不值得；本插件直接给"复制两个文件就能跑"的最小集。

## 本项目自己的实测

以下结论来自本机实验（Win10 + conhost + Windows Terminal + Win7 打包环境）：

1. conhost 默认 VT 位为 0（`GetConsoleMode → 0x3`），手动开启后 rich 从 16 色变真彩。
2. 渲染宽度等于终端宽度时，`Live` 每帧下漂一行；宽度减 1 修复。
3. rich 的 legacy 映射里 blue → `#000080`，黑底不可读。
4. textual 8.x 需要 Python ≥3.9；textual 打包 ~21 MB，rich ~9 MB（Py3.8）。
5. bubbletea v1.3.10 需要 Go 1.24，Win7 只能退到 v0.27.1；且强制 VT，Win7 启动即失败。
6. PyInstaller 自动收集 UCRT 不可靠，必须显式打包 `downlevel` 目录。

## 用户自己的笔记

- `Documents\Obsidian\zxw_obsidian\ai\设备网页逆向-自动化-打包经验.md`
- `Documents\Obsidian\zxw_obsidian\ai\ECN测试台自动化_win7-详细.md`
- `Desktop\AI\wtoe-device-config\`（run_all / cam_password / hk_config）

Win7 打包的四件套（3.8.10 / PyInstaller 5.13.2 / setuptools<81 / UCRT downlevel）
来自这些笔记的实测记录，插件只是把它脚本化。
