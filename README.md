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

导入前先准备好 `items.csv`。它必须包含 60 个有效词条。

## 创建词库 CSV

在项目目录下创建 `items.csv`。文件需要包含表头，并且正好有 60 个有效词条。

```powershell
@'
term,definition,phonetic,example,tags
opaque,hard to understand,oʊˈpeɪk,The rule is opaque.,work
terse,brief,tɜːrs,Keep the output terse.,work
subtle,delicate or not obvious,sʌtl,There is a subtle difference.,work
# ...继续补足到 60 个有效词条
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

## 从 PDF 生成 CSV

如果每天的词表来自 `奶酪单词-中英词表.pdf`，可以让 Codex 读取 PDF 的可见内容，并生成符合本应用导入格式的 CSV。

推荐把 PDF 文件放在项目目录下，然后对 Codex 使用下面这段提示词。

```text
请读取当前项目目录下的「奶酪单词-中英词表.pdf」，根据 PDF 页面中实际显示的内容，生成一个可被本项目导入的 CSV 文件。

目标输出文件：

- items.csv

CSV 格式要求：

- 必须使用 UTF-8 编码。
- 必须包含表头：term,definition,phonetic,example,note,tags,source
- 每一行对应一个单词或短语。
- term 填英文单词或英文短语。
- definition 填中文释义。如果 PDF 中同一个词有多个中文释义，请用中文分号「；」合并。
- phonetic 填音标。如果 PDF 没有音标，留空。
- example 填例句。如果 PDF 没有例句，留空。
- note 填补充信息，例如词性、固定搭配、易混说明等；如果没有，留空。
- tags 填固定值：cheese
- source 填固定值：奶酪单词-中英词表.pdf

抽取规则：

- 只使用 PDF 中能看到的内容，不要凭空补充释义、例句或音标。
- 保持 PDF 中的单词顺序。
- 跳过页眉、页脚、页码、水印、广告、目录和无关说明文字。
- 如果一行里包含序号，只提取真正的单词和释义，不要把序号写入 term。
- 如果 PDF 中出现重复单词，只保留第一次出现的记录。
- 如果某个词条无法可靠判断英文 term 或中文 definition，请不要猜测，把它写入一个单独的 skipped_items.md，并说明跳过原因。
- CSV 字段中如果包含逗号、换行或英文双引号，必须按 CSV 标准正确转义。

完成后请输出：

- 生成的 CSV 文件路径。
- 成功生成的词条数量。
- 跳过的词条数量。
- 如有跳过项，列出 skipped_items.md 的路径。

不要修改项目代码，不要导入数据库，只生成 CSV 文件。
```

生成后导入：

```powershell
uv run echoes import .\items.csv
```

导入前会校验 CSV 中正好有 60 个有效词条。

## 导入词库

```powershell
uv run echoes import .\items.csv
```

导入成功后，数据库里原来的词条、卡片和复习记录都会被删除，只保留本次 CSV 中的 60 个有效词条。导入失败时，旧数据不会被改动。

示例输出：

```text
ok rows=60 items=60 cards=60 deleted=60/60/42 skipped=0
```

`deleted=旧词条/旧卡片/旧复习记录`。第一次导入时通常是 `deleted=0/0/0`。

CSV 里空的 `term` 和重复 `term` 会被跳过，计入 `skipped`。如果有效词条不是 60 个，导入会失败。

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
items=60 cards=60 due=60 reviews=0
```

含义：

- `items`：当前批次词条数量。
- `cards`：当前批次复习卡片数量。
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
