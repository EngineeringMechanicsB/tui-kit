# 示例

两个完整可跑的最小项目，复制改业务即可。都通过 `sys.path` 引用 `../assets/`
的组件，不需要额外安装。

## rich-cli —— 默认选择

```bash
cd rich-cli
python app.py --auto --dry-run     # 看计划
python app.py --list-hosts
python app.py --auto               # 真跑（会 ping 配置里的地址）
```

演示：配置生成、`--auto` / `--steps` / `--dry-run`、步骤表、日志、报告、退出码。
适合：批量巡检、设备配置、上传下载、任何"跑一串步骤"的工具。
Win7 可用。

## textual-app —— 需要全屏时

```bash
cd textual-app
python app.py            # 全屏，点开始
python app.py --auto     # 全屏并自动开始
python app.py --rich     # 没有 textual 时的降级路径
```

演示：`run_tasks` 接步骤列表、标签页、统计卡、日志页、报告页、失败步骤。
适合：需要按钮/键盘/长时间盯着的工具。**仅 Win10/11。**

## 抄哪个

| 你的需求 | 起点 |
|---|---|
| 一条命令跑完，要日志和报告 | `rich-cli/` |
| 要按钮、进度面板、实时日志 | `textual-app/` |
| 两个都要 | rich 做业务，textual 做可选外壳（参考牌识升级工具） |

两个示例都遵守 SKILL.md 的"交付标准"：配置、自动模式、dry-run、退出码、日志、报告。
