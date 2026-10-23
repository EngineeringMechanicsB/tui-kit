# tui-kit

**给 Claude Code 用的 Windows 命令行工具构建套件。**
写脚本时一次解决三件事：Win10/11 上好看、Win7 上能跑、最后能打成单文件 exe。

```
rich / textual 选型  →  可复制组件  →  一键 Win7 打包  →  交付前检查
```

---

## 这个插件解决什么

每次写产线/运维脚本，都要重新踩同一批坑：

- 中文表格错位（`str.ljust` 按 1 列算，中文占 2 列）
- 进度条每次刷新往下滚一行（渲染宽度 = 终端宽度）
- Win7 控制台把颜色打成 `←[32m`，emoji 变方框
- 打包到 Win7 报 `api-ms-win-core-path-l1-1-0.dll` 缺失、`pkg_resources` 缺失、UCRT 缺失
- 菜单、步骤表、结果卡片在每个新脚本里重写一遍

`tui-kit` 把这些固化成：**一套选型规范 + 一套能直接复制的组件 + 一个打包脚本 + 一个审查 agent**。

## 能力一览

| 能力 | 说明 |
|---|---|
| 选型矩阵 | rich / textual / 纯文本 各自适用场景，含实测代码量与体积 |
| 运行时组件 | VT 探测、主题、宽度修正、菜单、表格、步骤表、进度、汇总卡片 |
| 配置系统 | 首次运行生成带注释配置，之后自动读取；命令行只做覆盖 |
| 自动模式 | `--auto` / `--steps` 无人值守执行，失败返回非零退出码 |
| 报告 | 每次运行产出 Markdown / HTML / JSON 报告 + 带时间戳日志 |
| 全屏界面 | 成品执行器：标签页、按钮、进度、统计卡、报告页 |
| Win7 打包 | 自动校验 Python 3.8.10 / PyInstaller 5.13.2 / setuptools<81 |
| UCRT 打包 | 显式打入 `downlevel` 目录，裸 Win7 免装 VC++ 运行库 |
| 自检 | 打完用 `archive_viewer` 验证 `ucrtbase.dll` 真的在包里 |
| 审查 agent | 只读检查终端兼容、编码、打包配置 |

## 安装

### 方式一：技能目录（最简单）

把仓库整个文件夹复制到：

```
Windows:  C:\Users\<用户名>\.claude\skills\tui-kit\
macOS/Linux: ~/.claude/skills/tui-kit/
```

确保最终结构是 `...\skills\tui-kit\.claude-plugin\plugin.json`（不要多套一层目录）。

然后在 Claude Code 里执行：

```
/reload-plugins
```

### 方式二：Marketplace

```bash
/plugin marketplace add EngineeringMechanicsB/tui-kit
/plugin install tui-kit@tui-kit-market
```

本地目录也可以：

```bash
/plugin marketplace add D:\tools\tui-kit
/plugin install tui-kit@tui-kit-market
```

### 方式三：只复制组件，不装插件

不需要 Claude Code，也不需要插件系统：

```bash
cp skills/tui-builder/assets/{tui_boot.py,ui_kit.py} your_project/
```

```python
from ui_kit import UI

ui = UI()
ui.banner("设备批量配置", "10.0.0.11 · 3 个任务")
ui.run_steps([("改密码", do_pwd), ("恢复出厂", do_reset)])
ui.summary(ok=2, fail=0, skip=0)
```

## 使用

装好后可以显式调用：

```
/tui-kit:tui-builder
```

也可以直接对 Claude 说：

- “用 tui-kit 写一个设备批量配置脚本，要进度条和结果表”
- “把这个脚本改成 Win7 能跑的”
- “打包成 Win7 单文件 exe，x64 和 x86 都要”
- “审查一下这个脚本的终端兼容性”

## 目录结构

```
tui-kit/
├── .claude-plugin/
│   ├── plugin.json              # 插件清单
│   ├── marketplace.json         # 同时作为 marketplace
│   └── icon.png
├── skills/tui-builder/
│   ├── SKILL.md                 # 主规范
│   ├── references/
│   │   ├── decision.md          # rich / textual / 纯文本怎么选
│   │   ├── rich-patterns.md     # rich 组件配方
│   │   ├── textual-patterns.md  # textual 骨架、CSS、响应式、测试
│   │   ├── win7.md              # Win7 运行时兼容全表
│   │   ├── packaging.md         # 打包全流程与排错
│   │   ├── checklist.md         # 交付前检查清单
│   │   └── sources.md           # 资料来源与取舍
│   └── assets/
│       ├── tui_boot.py          # VT 探测 + 主题 + 宽度修正
│       ├── ui_kit.py            # 菜单 / 表格 / 步骤表 / 汇总
│       ├── app_skeleton.py      # textual 全屏骨架
│       ├── build_win7.py        # 一键 x64 + x86 打包
│       └── templates/script_template.py
└── agents/tui-reviewer.md       # 只读审查 agent
```

## 配置 / 自动模式 / 报告

```python
from config_kit import Config
from report_kit import Reporter
from ui_kit import UI

cfg = Config("mytool", DEFAULTS, DOCS).load()   # 首次运行生成 mytool_config.json
ui = UI()
rep = Reporter("mytool", target=cfg["host"], out_dir="reports", log_dir="logs").start()
ui.log_fp = rep.log_fp

results = ui.run_steps([("上传", do_upload), ("安装", do_install)])
for name, ok, detail in results:
    rep.step(name, ok, detail)
rep.finish()          # reports/*.html + *.md + *.json, logs/*.log
```

自动模式：

```bash
python app.py --auto                    # 按配置里的 steps 跑完
python app.py --steps upload,install    # 只跑指定步骤
python app.py --dry-run                 # 只打印计划
```

## 打包示例

```bash
# 一次性环境（只在需要打包的机器上）
pip install "rich==14.0.0" "pyinstaller==5.13.2" "setuptools<81"

# 打 x64 + x86
python skills/tui-builder/assets/build_win7.py \
    --entry run_all.py --name mytool \
    --python-x64 D:\python38-x64\python.exe \
    --python-x86 D:\python38-x86\python.exe

# 只校验已有 exe
python skills/tui-builder/assets/build_win7.py --check dist\mytool-x64.exe
```

输出：

```
[OK] dist\mytool-x64.exe  9.2 MB
[OK] dist\mytool-x86.exe  8.6 MB
```

## 实测数据

| 项 | 结果 |
|---|---|
| rich 版工具 exe | 9.2 MB（x64）/ 8.6 MB（x86），Python 3.8.10 |
| textual 版工具 exe | ~21 MB，仅 Win10/11 |
| 启动开销 | onefile 解压 1–2 秒 |
| UCRT 校验 | 两个架构均通过 `archive_viewer` 检查 |
| 插件校验 | `claude plugin validate --strict` 通过 |

## 已知限制

- **textual 在 conhost 下中文会错位**：这是 Windows 老控制台的宽字符模型问题
  （Textual [#5456](https://github.com/Textualize/textual/issues/5456)、
  [#4974](https://github.com/Textualize/textual/issues/4974)），用 Windows Terminal 正常。
- **Win7 不能用 textual**：需要 Python ≥3.9 + VT 终端。
- **Win7 打包必须 Python 3.8.10**：3.9+ 依赖 Win8 专属 API。
- 插件安装若用本地 marketplace，**源目录移动后需要重新 add**。

## 参考

- Rich — https://rich.readthedocs.io/
- Textual — https://textual.textualize.io/
- PyInstaller — https://pyinstaller.org/
- Claude Code Plugins — https://code.claude.com/docs/en/plugins-reference

## License

MIT — 见 [LICENSE](LICENSE)。
