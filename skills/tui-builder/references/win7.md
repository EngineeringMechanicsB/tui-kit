# Win7 运行时兼容

目标：Win7 上**能清晰读、功能完整**即可，不追求好看。
Win10/11 走同一条代码路径，只是自动升级到真彩色。

## 1. 控制台能力探测

```python
mode = GetConsoleMode(stdout)
vt = mode & ENABLE_VIRTUAL_TERMINAL_PROCESSING(0x0004)
```

- Win10/11 conhost：支持 VT，但**默认没开**
- Win7 conhost：不支持，`SetConsoleMode` 调用失败
- 陷阱：Win7 上某些 wrapper 让调用返回"成功"，但位没置上 → **必须回读**

`tui_boot.enable_vt()` 已实现（设置 → 回读 → 返回布尔）。

## 2. 三种渲染路径

| 环境 | 路径 | 外观 |
|---|---|---|
| Win10/11 + VT 开启 | rich ANSI 真彩 | 完整效果 |
| Win7 / VT 关闭 | rich `LegacyWindowsTerm`（`SetConsoleTextAttribute`） | 16 色，文字完整 |
| 没装 rich | 纯文本 print | 无颜色 |

rich 自己会判断，不需要我们写分支。唯一要自己做的是**先开 VT**。

## 3. 16 色配色规则

老控制台只有 16 个固定色位，RGB 由控制台属性决定，程序改不了。
cmd 默认调色板的深蓝 `#000080` 黑底对比度约 2:1 → 几乎看不见。

| ANSI | 老控制台实际 | 说明 |
|---|---|---|
| 30 / 90 | 灰 `0x08` | 纯黑等于隐形，只用于压暗 |
| 31 / 91 | 亮红 `0x0C` | |
| 32 / 92 | 亮绿 `0x0A` | |
| 33 / 93 | 亮黄 `0x0E` | |
| **34 / 94** | **亮青 `0x0B`** | 蓝色系一律换亮青 |
| 35 / 95 | 亮品红 `0x0D` | |
| **36 / 96** | **亮青 `0x0B`** | |
| 37 / 97 | 亮白 `0x0F` | |

规则：
- 正文一律用"亮"色位
- **不要用 blue / dim**
- `dim` 在老控制台是清掉亮度位，等于颜色失效
- 用 `bright_black` 表示灰色

rich 主题（`tui_boot.THEME`）已经按这个规则写：
`ok=bold green / err=bold red / warn=bold yellow / info=cyan / title=bold magenta / muted=bright_black`。

## 4. 宽度修正（必做）

症状：Live/Progress 每刷新一次，整块内容往下滚一行。

原因：渲染宽度 = 终端宽度时，最后一个字符会触发自动换行，rich 再补 `\n`
就多一行。

修法：`console.width = console.width - 1`（仅在 `console.is_terminal` 时）。
现代终端同样适用，视觉上只是右边留 1 格。

## 5. emoji 与符号

老控制台字体没有 emoji 字形 → 显示成方框或问号。

规则：
- 状态标记用 ASCII：`[OK] [XX] [!!] [i] [--]`
- 分隔符用 `- = | +`，不要 `─ │ ┌ ┐ ✓ ✗ ●`
- 必须用符号时，先做替换表：

```python
MAP = {"✅": "[OK]", "❌": "[XX]", "⚠️": "[!!]", "⏳": "[..]", "ℹ️": "[i]"}
```

`tui_boot` 已经只用 ASCII 标记。

## 6. 中文宽度

手写对齐必须按东亚宽度算：

```python
import unicodedata
def disp_width(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)
```

`str.ljust(n)` 把中文当 1 列，一定错位。
rich / textual 内部已处理，只有纯文本兜底需要自己算（`ui_kit._pad`）。

## 7. 编码

| 场景 | 规则 |
|---|---|
| 管道 / 重定向输出 | `sys.stdout.reconfigure(encoding="utf-8")` |
| 真实控制台（tty） | **不要动**，Windows 用 `WriteConsoleW` |
| 读写配置文件 | 依次尝试 `utf-8` → `gb2312` → `replace` |
| 写回配置文件 | 用读出来的原编码写回，别统一转 UTF-8 |
| 给 Win7 记事本看 | 用 GBK 存，或加 UTF-8 BOM |

`tui_boot.setup_stdio()` 已按这个规则实现。

## 8. 输入

- 只用 `input()` / `getpass`
- 不用 `msvcrt.kbhit()` 做方向键菜单：老控制台 + 中文输入法会双触发
- 管道调用（`echo 1 | app.exe`）：`input()` 抛 `EOFError`，要捕获后取默认值
- 交互脚本被无终端环境调用时，提前判断 `sys.stdin.isatty()`，直接走非交互分支

## 9. 字体与窗口（现场可调，程序管不到）

- 字体：控制台属性 → 字体 → 新宋体 / Consolas + 雅黑
- 窗口与缓冲区大小：属性 → 布局（缓冲区高度建议 ≥300，否则滚不动）
- 16 色 RGB：属性 → 颜色（改的是这台机器，不是程序）
- 这些都是**用户侧设置**，文档里写一句即可，别试图用程序改

## 10. 自查清单（Win7 视角）

- [ ] 用 `--no-vt` 模式（或真机）跑一遍：无 ANSI 残留、无方框
- [ ] 每个状态都有 ASCII 标记，不只靠颜色区分
- [ ] 表格在 80 列窗口下不折行错位
- [ ] 管道输出 `app.exe > out.txt` 中文不乱码
- [ ] `input()` 在无输入时不会崩（EOFError 有兜底）
- [ ] 进度条刷新不滚屏
