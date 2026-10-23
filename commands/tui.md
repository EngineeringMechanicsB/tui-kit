---
description: 用 tui-kit 规范写或审查一个 Windows 命令行工具
argument-hint: [要做什么，例如：给 run_all.py 加进度表和报告]
allowed-tools: Bash Read Write Edit Glob Grep
---

使用 `tui-builder` 技能完成下面的请求：

$ARGUMENTS

执行顺序：

1. 读 `skills/tui-builder/SKILL.md`，按"工作流"六步走。
2. 判断目标机有没有 Win7：有 → rich，不许引入 textual。
3. 从 `assets/` 或 `examples/` 选最接近的起点，不要从零写。
4. 完成后运行 `python skills/tui-builder/scripts/check_script.py <文件>`，
   有 E 级问题必须先修。
5. 汇报时给出：改了哪些文件、怎么运行、Win7 下会降级成什么样。
