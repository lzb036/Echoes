# Echoes

Echoes 是一个运行在 Windows 终端里的低存在感背单词应用，使用 Python、Textual、SQLite 和 FSRS 构建。

应用数据默认只保存在本机的单个 SQLite 文件中。界面保持黑底白字或默认终端配色，按 `Esc` 可以在背词界面和伪装构建日志界面之间快速切换。

## 环境要求

- Windows
- PowerShell
- Python 3.12 或更新版本
- uv

检查 Python 和 uv：

```powershell
python --version
uv --version
```

## 快速开始

```powershell
cd D:\Echoes
uv sync
uv run echoes doctor
uv run echoes import .\items.csv
uv run echoes
```

## 创建词库 CSV

在项目目录下创建 `items.csv`：

```powershell
@'
term,definition,phonetic,example,tags
opaque,hard to understand,oʊˈpeɪk,The rule is opaque.,work
terse,brief,tɜːrs,Keep the output terse.,work
subtle,delicate or not obvious,sʌtl,There is a subtle difference.,work
'@ | Set-Content -Encoding UTF8 .\items.csv
```

支持的 CSV 表头：

```csv
term,definition,phonetic,example,note,tags,source
```

字段说明：

- `term`：单词或短语，必填。
- `definition`：释义或答案文本，可选。
- `phonetic`：音标，可选。
- `example`：例句，可选。
- `note`：额外备注，可选。
- `tags`：标签，可选，多个标签可以用 `;` 或 `,` 分隔。
- `source`：来源，可选。

## 导入词库

```powershell
uv run echoes import .\items.csv
```

示例输出：

```text
ok rows=3 items=3 cards=3 skipped=0
```

导入会自动去重。重复导入同一个文件时，不会重复创建同一批卡片。

## 启动应用

```powershell
uv run echoes
```

默认按键：

- `Space`：显示答案。
- `1`：Again，忘记。
- `2`：Hard，困难想起。
- `3`：Good，正常想起。
- `4`：Easy，轻松想起。
- `Esc`：开启或关闭伪装日志界面。
- `q`：退出。

默认界面会尽量保持安静。你会先看到当前单词，按 `Space` 显示答案，再按 `1` 到 `4` 进行评分。

## 老板键

默认老板键是 `Esc`。

按下后，应用会切换到滚动的伪装构建日志界面。再次按下 `Esc` 会恢复到原来的背词状态，包括当前卡片和答案显示状态。

切换老板键不会写入复习记录，也不会重置当前卡片。

修改老板键：

```powershell
uv run echoes config set boss_key f12
```

恢复默认老板键：

```powershell
uv run echoes config set boss_key escape
```

修改按键配置后，需要重新启动应用。

## 显示提示

默认情况下，界面提示会尽量少。

开启提示：

```powershell
uv run echoes config set show_help true
```

关闭提示：

```powershell
uv run echoes config set show_help false
```

修改后需要重新启动应用。

## 伪装日志风格

当前支持这些伪装日志风格：

- `docker`
- `git`
- `pytest`

设置方式：

```powershell
uv run echoes config set fake_log_profile docker
uv run echoes config set fake_log_profile git
uv run echoes config set fake_log_profile pytest
```

修改后需要重新启动应用。

## 查看统计

```powershell
uv run echoes stats
```

示例输出：

```text
items=3 cards=3 due=3 reviews=0
```

含义：

- `items`：已导入词条数量。
- `cards`：复习卡片数量。
- `due`：当前到期可复习卡片数量。
- `reviews`：已保存复习记录数量。

## 数据库

Windows 下默认数据库路径：

```powershell
%LOCALAPPDATA%\Echoes\echoes.db
```

通常类似：

```powershell
C:\Users\<username>\AppData\Local\Echoes\echoes.db
```

所有本地数据都保存在这一个 SQLite 文件中：

- 词条
- 卡片
- FSRS 复习状态
- 复习历史
- 应用设置

如果删除这个 `.db` 文件，对应数据库里的数据也会被删除。

使用指定数据库文件：

```powershell
uv run echoes --db .\data\test.db import .\items.csv
uv run echoes --db .\data\test.db
```

也可以通过环境变量指定数据库路径：

```powershell
$env:ECHOES_DB_PATH = "D:\Echoes\data\custom.db"
uv run echoes
```

## 配置

设置配置项：

```powershell
uv run echoes config set boss_key escape
```

读取单个配置项：

```powershell
uv run echoes config get boss_key
```

读取所有配置项：

```powershell
uv run echoes config get
```

当前常用配置项：

- `boss_key`
- `show_help`
- `fake_log_profile`
- `review_limit`
- `daily_new_limit`

## 环境检查

检查运行环境和数据库路径：

```powershell
uv run echoes doctor
```

示例输出：

```text
ok db=C:\Users\<username>\AppData\Local\Echoes\echoes.db
python=3.12.3
textual=8.2.5
fsrs=unknown
```

## 开发检查

运行测试：

```powershell
uv run pytest
```

运行 lint：

```powershell
uv run ruff check .
```

检查格式：

```powershell
uv run ruff format . --check
```

格式化文件：

```powershell
uv run ruff format .
```
