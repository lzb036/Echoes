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
term,definition,phonetic,example,note,tags,source
```

必填字段：

- `term`：单词或短语。

常用字段：

- `definition`：释义或答案。
- `phonetic`：音标。
- `example`：例句。
- `note`：备注。
- `tags`：标签。
- `source`：来源。

示例：

```csv
term,definition,phonetic,example,note,tags,source
opaque,hard to understand,,The rule is opaque.,,daily,items.csv
terse,brief,,Keep the output terse.,,daily,items.csv
subtle,delicate or not obvious,,There is a subtle difference.,,daily,items.csv
```

继续补足到 60 个有效词条后，再运行 `import.cmd`。

CSV 里空的 `term` 和重复 `term` 会被跳过。如果有效词条不是 60 个，导入会失败。

## 导入规则

每次导入都会完全覆盖旧数据。

导入成功后：

- 旧词条会被删除。
- 旧卡片会被删除。
- 旧复习记录会被删除。
- 数据库只保留本次 CSV 的 60 个词条。

导入失败时，旧数据不会被改动。

## 复习规则

每个词需要过关 3 次。

- `Good` / `Easy`：当前词过关次数加 1。
- `Hard`：当前词过关次数不变。
- `Again`：当前词过关次数清零。
- 到 `3/3` 后，这个词不会再出现。

右上角第一行表示整批 60 个词的完成数，例如 `1/60`；第二行表示当前词的过关次数，例如 `1/3`。

## 文件说明

便携版文件夹里常用文件：

- `start.cmd`：启动应用。
- `import.cmd`：导入同目录下的 `items.csv`。
- `doctor.cmd`：检查运行状态和数据库路径。
- `items.csv.template`：CSV 模板。
- `data\`：本地数据库目录。

换新设备时，直接复制整个 `Echoes` 文件夹即可。

## 按键

- `Space`：显示答案。
- `1`：Again。
- `2`：Hard。
- `3`：Good。
- `4`：Easy。
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
