# JMAG 可视化启动脚本使用指南

## 1. 脚本实现的功能

`open_jmag_fast.py` 用于在 Windows 中可视化启动 JMAG-Designer，可选择直接打开项目、打开项目副本，或在明确确认后用副本替换原项目。

它支持以下功能：

- 不指定项目时，只启动 JMAG-Designer。
- 直接打开指定的 `.jproj` 项目。
- 同时复制 `.jproj` 和同名 `.jfiles` 目录，再打开副本。
- 按需检查 `.jproj` 中引用的 `.jplot` 结果文件。
- 当 JMAG 弹出 `Missing Result Files` 对话框时，自动点击 **OK**。
- 可选等待 JMAG 自动化上下文可用，便于后续脚本继续控制模型或 Study。
- 在具有双重显式确认的模式下，打开副本后删除原 `.jproj` 和原 `.jfiles`。

## 2. 相比原版的速度优化

默认启动路径不再读取整个 `.jproj`，也不再递归扫描 `.jfiles`。仅在使用 `--handle-missing-results` 时执行结果检查；`copy-delete-original` 因涉及删除，会强制检查。

其他优化包括：

- 用 `next(rglob(...), None)` 判断是否存在结果文件，找到第一个就停止，不再建立完整列表。
- 删除 `pywinauto` 依赖，使用更轻量的 Win32 API 查找和确认对话框。
- 对话框轮询间隔由 0.5 s 缩短为 0.25 s。
- 在启动 JMAG 前并行启动对话框监视线程，避免 JMAG 被模态窗口阻塞时主线程无法继续。
- 只有使用 `--attach` 时才导入并轮询 `JMAGContext`。
- JMAG 环境和启动 API 改为延迟加载；查看 `--help` 或导入诊断/复制函数时不再初始化 JMAG。
- `--attach` 的轮询间隔由 1 s 缩短为 0.5 s。

因此，日常打开正常项目时应使用默认快速模式；只有确实存在缺失结果文件时才开启检查。

## 3. 环境要求

脚本应在配置好 JMAG Python 环境的 Windows 终端中运行，并满足：

1. `_jmag_user_env.py` 可被当前脚本导入。
2. `configure_environment()` 能正确设置 JMAG Python/API 路径。
3. `jmag_functions.project` 中存在：
   - `DEFAULT_DESIGNER_EXECUTABLE`
   - `launch_project_in_visible_designer`
4. 使用 `--attach` 时，`jmag_functions.session.JMAGContext` 可用。

假设脚本保存为：

```text
C:\Codex\jmag-script-skill\open_jmag_fast.py
```

以下命令均可在 PowerShell 或 CMD 中执行。

## 4. 常用命令

### 4.1 只启动 JMAG，不打开项目

```powershell
python C:\Codex\jmag-script-skill\open_jmag_fast.py
```

### 4.2 快速打开原项目（推荐默认方式）

```powershell
python C:\Codex\jmag-script-skill\open_jmag_fast.py "C:\JMAG\Motor.jproj"
```

此模式只检查项目文件是否存在，然后立即请求 JMAG 打开，不检查 `.jplot`。

### 4.3 打开原项目，并处理缺失结果文件

```powershell
python C:\Codex\jmag-script-skill\open_jmag_fast.py "C:\JMAG\Motor.jproj" --handle-missing-results
```

脚本会：

1. 读取项目中的 `.jplot` 引用。
2. 检查同名 `Motor.jfiles` 目录。
3. 输出缺失项。
4. 在 JMAG 弹窗出现时自动点击 **OK**。

若 JMAG 启动较慢，可延长弹窗等待时间：

```powershell
python C:\Codex\jmag-script-skill\open_jmag_fast.py "C:\JMAG\Motor.jproj" --handle-missing-results --dialog-timeout 30
```

### 4.4 创建并打开默认名称的项目副本

```powershell
python C:\Codex\jmag-script-skill\open_jmag_fast.py "C:\JMAG\Motor.jproj" --mode copy
```

默认创建：

```text
C:\JMAG\Motor_automation_copy.jproj
C:\JMAG\Motor_automation_copy.jfiles\
```

如果目标已存在，脚本会拒绝覆盖。

### 4.5 创建并打开指定路径的副本

```powershell
python C:\Codex\jmag-script-skill\open_jmag_fast.py "C:\JMAG\Motor.jproj" --mode copy --copy-target "C:\JMAG\Working\Motor_test.jproj"
```

`C:\JMAG\Working` 必须已经存在。

### 4.6 等待 JMAG 自动化接口可连接

```powershell
python C:\Codex\jmag-script-skill\open_jmag_fast.py "C:\JMAG\Motor.jproj" --attach --timeout 60
```

适用于本脚本后面还要执行自动建模、修改 Study 或导出结果的情况。仅希望人工查看项目时不要加 `--attach`，否则会产生额外轮询时间。

### 4.7 打开副本并删除原项目（高风险，不建议作为日常命令）

```powershell
python C:\Codex\jmag-script-skill\open_jmag_fast.py "C:\JMAG\Motor.jproj" --mode copy-delete-original --confirm-delete-original
```

该模式会删除：

```text
C:\JMAG\Motor.jproj
C:\JMAG\Motor.jfiles\
```

注意：

- `--confirm-delete-original` 是强制的第二重确认。
- 该模式会强制检查缺失结果。
- 如果缺失结果对话框未被成功确认，原项目不会被删除。
- 删除不是回收站操作，运行前应另做备份。

## 5. 参数说明

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `project` | 无 | 要打开的 `.jproj` 路径；省略时只启动 JMAG |
| `--mode` | `original` | `original`、`copy` 或 `copy-delete-original` |
| `--copy-target` | 自动命名 | 副本 `.jproj` 的完整路径 |
| `--handle-missing-results` | 关闭 | 检查 `.jplot` 并自动处理缺失结果弹窗 |
| `--dialog-timeout` | 15 s | 等待缺失结果弹窗的时间 |
| `--attach` | 关闭 | 等待 `JMAGContext.from_current()` 成功 |
| `--timeout` | 30 s | `--attach` 的最长等待时间 |
| `--confirm-delete-original` | 关闭 | 允许 `copy-delete-original` 删除原项目 |

## 6. Python 代码中调用

快速打开：

```python
from pathlib import Path
from open_jmag_fast import open_jmag_window

open_jmag_window(Path(r"C:\JMAG\Motor.jproj"))
```

检查缺失结果并等待自动化上下文：

```python
open_jmag_window(
    Path(r"C:\JMAG\Motor.jproj"),
    timeout=60,
    handle_missing_results=True,
    dialog_timeout=30,
    attach=True,
)
```

打开副本：

```python
open_jmag_window(
    Path(r"C:\JMAG\Motor.jproj"),
    mode="copy",
    copy_target=Path(r"C:\JMAG\Working\Motor_test.jproj"),
)
```

## 7. 推荐使用策略

- 项目及结果完整：使用默认命令，不加任何检查参数。
- 已知项目缺少 `.jplot`：加 `--handle-missing-results`。
- 自动化脚本必须等项目加载完成：再加 `--attach`。
- 要保护原项目：使用 `--mode copy`。
- 除非工作流明确要求替换原件，否则不要使用 `copy-delete-original`。

## 8. 已知限制

- 自动点击依赖英文对话框标题包含 `Missing Result Files`；非英文版 JMAG 需要调整标题关键字。
- `.jproj` 是二进制/混合格式时，正则扫描只能识别其中可读的 `.jplot` 字符串。
- 默认快速模式不会预判缺失结果；如果 JMAG 弹窗，需要人工点击 **OK**，或重新使用 `--handle-missing-results` 启动。
- `--attach` 判断的是当前 JMAG 自动化上下文可用；如果同时打开多个 JMAG 实例，连接目标取决于 `JMAGContext.from_current()` 的实现。
