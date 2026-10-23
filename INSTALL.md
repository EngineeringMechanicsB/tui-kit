# 安装到另一台机器

三种方式，按需要选。目标机器需要 **Claude Code**；如果只是用组件，不需要 Claude Code。

## 0. 带什么过去

打包整个 `claude-plugin-tui-kit-20261023` 文件夹（zip 也行）。
解压后必须能直接看到 `.claude-plugin\plugin.json`，**不要多套一层目录**。

---

## 方式 A：技能目录（最简单，不需要 git）

1. 把文件夹改名/复制为：

```
C:\Users\<用户名>\.claude\skills\tui-kit\
```

最终结构：

```
C:\Users\<用户名>\.claude\skills\tui-kit\
├── .claude-plugin\
│   ├── plugin.json
│   └── marketplace.json
├── skills\
│   └── tui-builder\
│       ├── SKILL.md
│       ├── references\
│       └── assets\
├── agents\
└── README.md
```

2. 启动（或已在运行则执行）：

```
/reload-plugins
```

3. 验证：

```
/tui-kit:tui-builder
```

或问一句"tui-kit 装好了吗"，Claude 应能读到 `tui-builder` 技能。

> 卸载：删掉这个文件夹，或 `claude plugin disable tui-kit@skills-dir`。

---

## 方式 B：marketplace（可更新、多人共用）

把文件夹放到任意位置，例如 `D:\tools\tui-kit`，然后：

```
/plugin marketplace add D:\tools\tui-kit
/plugin install tui-kit@tui-kit-market
```

如果是 git 仓库：

```
/plugin marketplace add yourname/tui-kit
/plugin install tui-kit@tui-kit-market
```

更新时：`/plugin marketplace update tui-kit-market` + `/plugin update`。
**注意**：manifest 有 `version` 字段，发新版必须 bump，否则用户拿不到更新。

---

## 方式 C：临时会话

```bash
claude --plugin-dir "D:\tools\tui-kit"
```

只对这次会话生效，适合试用。必须指向**插件根**（含 `.claude-plugin` 的那层）。

---

## 目标机器上的 Python 环境（写脚本/打包时用）

只有需要**打包 exe** 时才要：

```bat
:: Python 3.8.10（Win7 兼容的最后版本）
python-3.8.10-amd64.exe /quiet InstallAllUsers=0 TargetDir=D:\python38-x64 Include_pip=1 PrependPath=0
python-3.8.10.exe       /quiet InstallAllUsers=0 TargetDir=D:\python38-x86 Include_pip=1 PrependPath=0

D:\python38-x64\python.exe -m pip install "rich==14.0.0" "pyinstaller==5.13.2" "setuptools<81"
D:\python38-x86\python.exe -m pip install "rich==14.0.0" "pyinstaller==5.13.2" "setuptools<81"
```

安装包：
- https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe
- https://www.python.org/ftp/python/3.8.10/python-3.8.10.exe

只在 Win10/11 上跑、不需要兼容 Win7 的话，用当前 Python + 最新 rich/textual 即可。

---

## 校验插件是否合法

```bash
claude plugin validate "C:\Users\<用户名>\.claude\skills\tui-kit" --strict
```

退出码 0 = 通过。常见失败：

| 报错 | 原因 |
|---|---|
| `No manifest found` | 指到了 marketplace 根，不是插件根 |
| `invalid name` | 名字不是 kebab-case，或撞了 `claude-` / `anthropic-` 前缀 |
| 组件没被发现 | `skills/`、`agents/` 被放进了 `.claude-plugin/` |
| 路径越界 | manifest 里用了绝对路径或 `..` |

---

## 只想要组件、不装插件

把这两个文件复制进你的项目目录即可：

```
skills\tui-builder\assets\tui_boot.py
skills\tui-builder\assets\ui_kit.py
```

```python
from ui_kit import UI
ui = UI()
ui.banner("标题")
```

它们只依赖标准库 + rich，单文件复制也能用。
