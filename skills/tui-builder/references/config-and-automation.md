# 配置化 / 自动模式 / 报告

一条原则：**参数不写在代码里，也不靠人敲命令行。**
第一次运行生成配置文件，之后每次都读它；命令行只做临时覆盖。

## 1. 配置文件长什么样

JSONC：合法 JSON + `//` 注释。每项上面一行中文说明，记事本可读可改。

```jsonc
{
  // 牌识升级 配置文件 —— 改完保存即可，脚本每次运行都会读。
  // 命令行参数优先于本文件；删掉某一项 = 用脚本内置默认值。

  // 设备 IP；连不上时先 ping 确认在线
  "host": "192.168.77.230",
  // SSH 端口
  "port": 22,
  // 默认执行步骤
  "steps": ["upload", "install", "reboot", "verify"],
  // 是否生成报告
  "report": true
}
```

规则：
- 注释只在字符串外生效，值里带 `//`（路径、URL）不会被误伤
- 删除某项 → 下次运行自动补回默认值
- 脚本不认识的多余项 → 原样保留
- 文件被改坏 → 备份成 `.bad-时间戳` 再用默认值重建

## 2. 生成与读取（`config_kit.py`）

```python
from config_kit import Config

DEFAULTS = {
    "host": "192.168.77.230",
    "port": 22,
    "steps": ["upload", "install", "reboot", "verify"],
    "report": True,
}
DOCS = {
    "host": "设备 IP；连不上时先 ping 确认在线",
    "port": "SSH 端口",
    "steps": "默认执行哪些步骤",
    "report": "true = 生成报告",
}

cfg = Config("pai_shi_upgrade", DEFAULTS, DOCS).load()   # 首次运行自动生成
print(cfg["host"])
```

`Config.load()` 的行为：
1. 文件不存在 → 生成（带注释）
2. 文件存在但缺项（脚本升级过）→ 合并默认值并写回
3. 解析失败 → `.bad-<时间戳>` 备份 + 用默认值重建

配置放在**脚本同目录**（便携，拷贝整个文件夹就能带走）。
没有写权限时自动退回用户目录。

## 3. 命令行只做覆盖

```python
ap = argparse.ArgumentParser()
ap.add_argument("--host", default=None, help="覆盖配置里的 IP")
ap.add_argument("--steps", default="", help="逗号分隔，只跑这几步")
ap.add_argument("--auto", action="store_true", help="自动模式，不弹菜单")
ap.add_argument("--save-config", action="store_true", help="把本次参数写回配置")
args = ap.parse_args()

if args.host:
    cfg["host"] = args.host          # 只改内存，不自动落盘
if args.save_config:
    cfg.save()
```

**为什么默认不落盘**：调试时随手 `--host x` 不该永久改掉现场配置。
需要记住时显式 `--save-config`。

## 4. 自动模式

三种触发方式，行为一致：不弹菜单、不读输入、跑完退出。

```bash
python app.py --auto                       # 用配置里的 steps
python app.py --steps upload,install       # 显式指定步骤
python app.py < run.txt                    # stdin 不是终端时视为自动
```

```python
interactive = (not args.auto
               and sys.stdin.isatty()
               and not args.version)
```

要点：
- 自动模式下**必须有非零退出码**表示失败，批量脚本据此统计
- 每一步失败要带原因，不要静默跳过
- 提供 `--dry-run`：只打印计划，不连接设备
- 提供 `--version` 之类只读动作，现场排查先用它

## 5. 步骤选择

```python
ALL_STEPS = ["upload", "install", "reboot", "verify"]
selected = ([s.strip() for s in args.steps.split(",") if s.strip()]
            or list(cfg["steps"]))
bad = [s for s in selected if s not in ALL_STEPS]
if bad:
    print("不认识的步骤：%s" % ",".join(bad))
    return 2
```

依赖关系靠**固定执行顺序**保证（列表顺序），不靠用户输入顺序。
例如 `verify` 一定在 `reboot` 之后，即使命令写成 `--steps verify,reboot`。

## 6. 日志

两种做法，按需要选：

```python
ui = UI()                       # 无日志
ui = UI(log_path="logs/x.log")  # UI 输出同时写文件
reporter = Reporter(...)        # 更完整：结果 + 报告
```

`ui_kit.UI` 的每个 print/banner/表格/步骤结果都会带时间戳进日志。
`run_steps` 额外记录每步耗时。

## 7. 报告（`report_kit.py`）

```python
from report_kit import Reporter

rep = Reporter("牌识升级", target=host,
               out_dir="reports", log_dir="logs",
               meta={"升级包": "V1.2.0"}).start()
rep.log("开始连接")
rep.step("上传", True, "12.3 MB / 3.2s", seconds=3.2)
rep.step("安装", False, "install.sh 退出码 1", seconds=1.1)
paths = rep.finish()
# {'log': ..., 'md': ..., 'html': ..., 'json': ...}
```

产出：

| 文件 | 用途 |
|---|---|
| `reports/<时间>_<目标>.md` | 贴到工单 / PR |
| `reports/<时间>_<目标>.html` | 浏览器打开，单文件无外链，带状态色 |
| `reports/<时间>_<目标>.json` | 机器读，做统计 |
| `logs/<时间>_<目标>.log` | 全过程日志 |

文件名带时间戳和目标，多台设备不会互相覆盖。
HTML 用内联样式，能直接发给别人或归档。

## 8. 完整骨架

```python
cfg = Config(APP, DEFAULTS, DOCS).load()
args = parse_args()
apply_overrides(cfg, args)

selected = pick_steps(cfg, args)
tasks = build_tasks(cfg, selected)       # [(名称, 回调)]

if args.dry_run:
    print_plan(tasks); return 0

reporter = Reporter(APP, target=cfg["host"], ...).start() if cfg["report"] else None
ui = UI(log_path=reporter.log_path if reporter else None)

if args.tui:
    ok = run_tasks(APP, tasks, report=reporter, ...)
else:
    results = ui.run_steps(tasks)
    ok = all(good for _, good, _ in results)

if reporter:
    for name, good, detail in results:
        reporter.step(name, good, detail)
    reporter.finish()
return 0 if ok else 1
```

## 9. 反模式

- ❌ 参数只写在开头常量里，现场要改就得改代码
- ❌ 自动模式还弹确认框（无人值守会卡死）
- ❌ 失败仍然 `exit 0`
- ❌ 报告文件名不带时间/目标，多台互相覆盖
- ❌ 把日志写进报告目录，混在一起
- ❌ 配置解析失败直接覆盖用户文件
