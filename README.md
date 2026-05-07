# Echoes

Echoes 是一个运行在 Windows 终端里的低存在感背单词工具。

普通使用不需要安装 Python，也不需要配置开发环境。下载 Windows 便携版，解压后双击脚本即可使用。

## 下载和启动

1. 从 GitHub Releases 下载 `Echoes-Windows-v版本号.zip`。
2. 解压 zip。
3. 打开解压后的 `Echoes` 文件夹。
4. 把当天的 `items.csv` 放进这个文件夹。
5. 双击 `import.cmd` 导入词表。
6. 双击 `start.cmd` 启动应用。

## items.csv

`items.csv` 必须包含表头，并且正好有 60 个有效词条。

支持的表头：

```csv
term,definition,phonetic,example,example_zh,note,tags,source
```

必填字段：

- `term`：单词或短语。

常用字段：

- `definition`：释义或答案。
- `phonetic`：音标。
- `example`：英文例句。
- `example_zh`：英文例句的中文翻译。
- `note`：备注。
- `tags`：标签。
- `source`：来源。

示例：

```csv
term,definition,phonetic,example,example_zh,note,tags,source
opaque,hard to understand,ˈoʊpeɪk,The rule is opaque.,这个规则很难理解。,,daily,items.csv
terse,brief,tɜːrs,Keep the answer terse.,让答案保持简洁。,,daily,items.csv
subtle,delicate or not obvious,ˈsʌtl,There is a subtle difference.,这里有一个细微差别。,,daily,items.csv
```

继续补足到 60 个有效词条后，再运行 `import.cmd`。

CSV 里空的 `term` 和重复 `term` 会被跳过。如果有效词条不是 60 个，导入会失败。

## 从 PDF 生成 items.csv

如果当天的单词来自 PDF，可以先把 PDF 发给 AI 工具，让它按下面提示生成 CSV 内容：

```text
请从这个 PDF 中提取适合今天背诵的 60 个英文单词或短语，并生成 items.csv 内容。

要求：
1. 只输出 CSV，不要解释。
2. 第一行必须是：term,definition,phonetic,example,example_zh,note,tags,source
3. 必须正好有 60 个有效词条。
4. term 不能为空，不能重复。
5. definition 使用 PDF 中的简明中文释义；如果过长，可以压缩到最核心含义。
6. phonetic 使用 PDF 中的音标，不要添加外层斜杠。
7. example 为每个单词生成一个简短英文例句，难度参考往届考研英语二阅读/翻译句子，但要更短、更清楚，适合背单词时快速理解。
8. example 必须自然包含 term；句子尽量 8 到 16 个英文词，不要写复杂长难句，不要使用生僻人名地名。
9. example_zh 是 example 的自然中文翻译，简洁准确。
10. note 留空。
11. tags 统一写 daily。
12. source 写 PDF 文件名。
```

拿到结果后，把内容保存为 `items.csv`，放到 `Echoes` 文件夹里，再运行 `import.cmd`。

## 导入规则

每次导入都会完全覆盖旧数据。

导入成功后：

- 旧词条会被删除。
- 旧卡片会被删除。
- 旧复习记录会被删除。
- 数据库只保留本次 CSV 的 60 个词条。

导入失败时，旧数据不会被改动。

## 复习规则

每个词按三次掌握推进，右上角会显示当前进度，例如 `1/3`。

- `Easy`：当前词进度加 1。
- `Hard`：当前词进度减 1，最低为 `0/3`。
- `Again`：直接退回 `0/3`。
- 到 `3/3` 后，这个词不会再出现。

单词不是固定 60 个一整轮。已经到期的复习词会优先于还没见过的新词出现；答错或困难的词会短间隔插回来，答对的词会随格子升高逐步拉长间隔。

默认间隔：

- `Again`：再做 1 张卡后回来。
- `Hard`：再做 2 张卡后回来。
- `Easy`：随进度升高，间隔约为 4、8 张卡。

单词会和音标显示在同一行，例如 `single  /ˈsɪŋɡl/`。

右上角第一行表示整批 60 个词的完成数，例如 `1/60`；第二行表示当前词的进度，例如 `1/3`。

## 文件说明

便携版文件夹里常用文件：

- `start.cmd`：启动应用。
- `import.cmd`：导入同目录下的 `items.csv`。
- `doctor.cmd`：检查运行状态和数据库路径。
- `items.csv.template`：CSV 模板。
- `data\`：本地数据库目录。

换新设备时，直接复制整个 `Echoes` 文件夹即可。

## 按键

- `e`：查看例句；第一次显示英文例句，再按一次显示中文翻译。显示答案前后都可使用。
- `Space`：显示释义，并进入评分状态；如果已经展开例句，释义会显示在例句上方。
- `1`：Again。
- `2`：Hard。
- `3`：Easy。
- `Esc`：切换伪装日志界面。
- `q`：退出。

## 数据位置

便携版默认把数据库放在：

```text
Echoes\data\echoes.db
```

源码开发时，不加 `--db` 也会默认使用项目根目录下的：

```text
data\echoes.db
```

手动测试可以用独立库：

```text
data\test.db
```

删除这些 `.db` 文件会删除对应词库和复习数据。

## 开发

开发、测试和打包说明见 [README-dev.md](README-dev.md)。
