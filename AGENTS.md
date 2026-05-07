# AGENTS.md

## 项目定位

这是一个基于 Python 的 Windows 终端背单词应用，核心目标是“低存在感、快速切换、当天完成”。应用默认运行在终端中，界面保持极简，避免花哨组件、明显学习软件视觉特征和大面积中文提示。

优先级如下：

1. 隐蔽性和即时切换。
2. 当天 60 个词的完成规则清晰可靠。
3. 本地数据安全和可迁移。
4. 操作效率。
5. 后续可扩展性。

项目当前只考虑 Windows。其他系统暂不作为兼容目标，也不需要为了跨平台牺牲 Windows 体验。

## 技术栈决策

首选技术栈：

- Python 3.12 或更新版本。
- Textual：用于构建终端 TUI。
- SQLite：单文件本地数据库。
- sqlite3 标准库：初期优先使用，避免过早引入 ORM。
- pytest：测试核心规则、数据库和导入逻辑。
- ruff：代码格式和静态检查。
- uv：推荐作为 Windows 下的依赖和虚拟环境管理工具。
- PyInstaller：用于生成 Windows 便携版发布包。

保留 Python + Textual 的理由：

- Textual 适合构建终端应用，能处理按键绑定、状态切换、定时器、滚动区域和组件状态。
- Windows 下 `curses` 体验和可用性不够理想，不作为首选。
- `prompt_toolkit` 适合命令行交互，但复杂界面、状态切换和日志滚动不如 Textual 清晰。
- SQLite 单文件满足隐私、本地化、备份和便携需求，当前不需要服务端数据库。

当前不使用 FSRS 或其他间隔重复库。产品目标是每天导入一批新词并当天背完，不保留旧批次，也不做跨天复习调度。

参考资料：

- Textual: https://textual.textualize.io/

## 产品原则

界面必须像一个普通终端工具，而不是学习应用。

- 默认黑底白字，或完全沿用用户终端主题。
- 不使用彩色大标题、卡片、进度环、动画装饰和醒目的学习文案。
- 终端标题不要出现 “word”, “vocabulary”, “study”, “flashcard” 等明显词汇。
- 主界面只显示当前必要信息：单词和音标、释义/例句、评分键、极少量状态。
- 可配置隐藏所有中文解释，只显示英文释义、例句或短提示。
- 支持一键暂停、恢复、退出，但默认快捷键不应和常见终端操作冲突太多。

隐蔽性边界：

- 可以实现应用内 Boss Key，切换到伪造的构建日志或代码日志视图。
- 不做进程伪装、系统级隐藏、窗口注入、键盘监听其他程序、绕过公司安全策略等行为。
- 不上传用户词库和复习记录。
- 不默认联网。

## Boss Key 设计

Boss Key 是第一核心功能。默认按键建议为 `escape`，但必须可配置。

行为要求：

- 在任意学习界面按下 Boss Key 后，必须立即进入伪装视图。
- 再次按下 Boss Key 后，必须恢复到原学习状态，包括当前单词、答案显示状态、光标焦点和计时状态。
- 切换不应重置当前卡片，不应触发复习评分，不应写入无关日志。
- 切换延迟目标低于 100ms。
- 伪装视图必须可以持续滚动输出，不应静止成一屏假内容。
- 伪装视图必须支持长时间停留，不能因为定时器或后台任务异常导致崩溃。

伪装视图内容建议：

- `docker build` 风格日志。
- `git fetch` / `git log` / `git diff --stat` 风格日志。
- `pytest` / `ruff` / `mypy` 风格日志。
- `npm install` / `pnpm build` 风格日志。
- Windows 友好的 PowerShell 输出风格。

伪装视图约束：

- 输出要朴素，避免过度戏剧化。
- 不出现真实公司名、真实仓库地址、真实 token、真实路径。
- 路径可使用类似 `C:\work\services\api`、`D:\repo\backend` 的假路径。
- 日志生成器必须是本地 deterministic/random 混合逻辑，不依赖网络。
- 日志速度要像真实命令：有快有慢，有阶段性停顿，有偶发 warning。
- 学习数据不得出现在伪装视图中。

建议实现：

- 使用显式状态维护 `study` 和 `cover` 两种模式。
- `App` 级别绑定 Boss Key，确保在任何子组件焦点下都能响应。
- 进入 `cover` 时不重置学习界面。
- 使用一个独立 `FakeLogService` 生成日志行。
- 伪装日志区只保留有限行数，例如 300 到 1000 行，避免内存无界增长。

## 学习流程

基础学习流程：

1. 从数据库取出一个未完成卡片。
2. 展示单词或提示。
3. 用户按键显示答案。
4. 用户使用 Again / Hard / Easy 评分。
5. 按三次掌握规则更新卡片状态。
6. 写入 review log。
7. 进入下一张未完成卡片。

默认按键建议：

- `e`: 分步显示例句，第一次显示英文例句，再按一次显示中文翻译；显示答案前后都可使用。
- `space`: 显示释义，并进入评分状态；若例句已展开，释义显示在例句上方。
- `1`: Again。
- `2`: Hard。
- `3`: Easy。
- `escape`: Boss Key。
- `q`: 退出或请求确认退出。
- `?`: 极简帮助，可配置关闭。

学习界面约束：

- 未显示答案前，不允许评分。
- 评分后立即持久化，不把关键复习数据只放在内存里。
- 没有未完成卡片时显示短文本，例如 `No items.`，不要展示庆祝动画。
- 底部必须显示当前可用按键，避免用户忘记操作。

## 三次掌握规则

每个词的核心状态是 `pass_count` 和 `next_review_turn`。

- 新导入词条从 `0/3` 开始。
- Again：忘记，`pass_count` 重置为 0。
- Hard：困难想起，`pass_count - 1`，最低为 0。
- Easy：想起，`pass_count + 1`，最多到 3。
- 当 `pass_count` 到 3 时写入 `completed_at`，该词不再出现在学习队列。

队列规则：

- 每评分一次，全局 `review_turn` 加 1。
- Again：隔 1 张卡再出现。
- Hard：隔 2 张卡再出现。
- Easy：随进度升高，分别隔 4、8 张卡再出现。
- 取下一张时优先选已经到 `next_review_turn` 的复习卡。
- 如果没有到期复习卡，则优先取未见过的新卡；如果没有新卡，再取未来最近的复习卡，不让界面空等。
- 这不是严格 60 个一整轮，而是错词快速插回，熟词逐步延后。

整体进度：

- 右上角第一行表示本批 60 个词里已经完成几个，例如 `1/60`。
- 右上角第二行表示当前词进度，例如 `1/3`。

## 数据库设计

数据库使用单个 SQLite 文件，建议默认路径：

- 默认环境：项目目录下 `data/echoes.db`。
- 手动测试：项目目录下 `data/test.db` 或命令行 `--db` 指定的路径。
- 便携版：包内 `data\echoes.db`。

### words

保存词条基础信息。

- `id` INTEGER PRIMARY KEY。
- `term` TEXT NOT NULL。
- `definition` TEXT。
- `phonetic` TEXT。
- `example` TEXT，英文例句。
- `note` TEXT，英文例句的中文翻译或其他备注。
- `tags` TEXT，JSON 数组字符串。
- `source` TEXT。
- `created_at` TEXT NOT NULL。
- `updated_at` TEXT NOT NULL。
- `archived_at` TEXT。

### cards

保存当前批次的卡片状态。

- `id` INTEGER PRIMARY KEY。
- `word_id` INTEGER NOT NULL。
- `card_type` TEXT NOT NULL。
- `pass_count` INTEGER NOT NULL DEFAULT 0。
- `next_review_turn` INTEGER NOT NULL DEFAULT 0。
- `completed_at` TEXT。
- `created_at` TEXT NOT NULL。
- `updated_at` TEXT NOT NULL。

### reviews

保存每次评分。

- `id` INTEGER PRIMARY KEY。
- `card_id` INTEGER NOT NULL。
- `rating` INTEGER NOT NULL。
- `reviewed_at` TEXT NOT NULL。
- `elapsed_ms` INTEGER。
- `pass_count_before` INTEGER NOT NULL。
- `pass_count_after` INTEGER NOT NULL。
- `review_turn` INTEGER NOT NULL。
- `next_review_turn` INTEGER。
- `is_manual` INTEGER NOT NULL DEFAULT 0。

### settings

保存配置。

- `key` TEXT PRIMARY KEY。
- `value` TEXT NOT NULL。
- `updated_at` TEXT NOT NULL。

数据库规则：

- 必须启用外键：`PRAGMA foreign_keys = ON`。
- 写入复习结果和 review log 必须在同一个事务中。
- 迁移脚本必须可重复执行。
- 不允许在 UI 回调中拼接 SQL 字符串。
- 复杂查询必须有测试。
- 数据导入前要做去重，按 `term` 判断重复。
- 当前产品采用每日覆盖导入：CSV 必须有 60 个有效词条，导入成功后删除旧词条、旧卡片和旧复习记录，只保留本次 60 个词条。
- 导入失败不得删除旧数据。

## 推荐目录结构

建议结构：

```text
echoes/
  pyproject.toml
  README.md
  README-dev.md
  AGENTS.md
  src/
    echoes/
      __init__.py
      app.py
      cli.py
      config.py
      models.py
      time_utils.py
      db/
        __init__.py
        connection.py
        migrations.py
        repositories.py
        schema.sql
      ui/
        __init__.py
        keymap.py
        fake_logs.py
      importers/
        __init__.py
        csv_importer.py
  tests/
    test_repositories.py
    test_csv_importer.py
    test_app_boss_key.py
    test_fake_logs.py
    test_keymap.py
```

分层规则：

- `ui` 只负责渲染、输入和状态切换。
- `db` 负责连接、迁移、持久化和三次掌握状态更新。
- `importers` 只负责数据导入清洗。
- `config` 负责路径、快捷键和用户设置。

## Windows 优先要求

必须优先适配：

- Windows Terminal。
- PowerShell。
- CMD 基础运行。
- 常见中文 Windows 环境。

Windows 注意事项：

- 路径处理必须使用 `pathlib.Path`。
- 不要硬编码 `/` 作为路径分隔符。
- 默认数据目录使用项目根目录下的 `data\`。
- 允许用 `ECHOES_HOME` 或 `ECHOES_DB_PATH` 显式覆盖数据库位置。
- 控制台编码问题要尽量避免，核心界面默认 ASCII 或简单 UTF-8 文本。
- 快捷键设计要考虑 `Ctrl+C`、`Ctrl+Z`、`Alt+Tab` 等 Windows 常见行为。
- 不依赖 Unix-only 命令。

## 配置设计

配置来源优先级：

1. 命令行参数。
2. 环境变量。
3. SQLite settings 表。
4. 默认值。

建议配置项：

- `boss_key`: 默认 `escape`。
- `theme`: 默认 `plain`。
- `show_help`: 默认 `false`。
- `show_chinese`: 默认 `true`。
- `fake_log_profile`: 默认 `docker`。
- `db_path`: 默认自动。
- `review_limit`: 默认 100。

## 命令行入口

建议命令：

- `echoes`: 启动应用。
- `echoes import items.csv`: 导入当天词库。
- `echoes stats`: 输出极简统计。
- `echoes doctor`: 检查数据库、依赖和终端环境。
- `echoes config set boss_key escape`: 修改配置。

命令行输出也要低调，不使用明显学习软件 branding。

便携版发布要求：

- 发布包优先使用 PyInstaller onedir。
- 便携版入口包含 `start.cmd`、`import.cmd` 和 `doctor.cmd`。
- 便携版脚本必须设置 `ECHOES_HOME` 到包内 `data` 目录。
- 普通用户文档优先描述下载 zip、放入 `items.csv`、双击脚本这条路径。
- Python、uv、pytest、ruff 和打包说明放在开发文档中。

## 开发计划

### 阶段 0：项目骨架

目标：

- 创建 Python 包结构。
- 配置 `pyproject.toml`。
- 加入 ruff 和 pytest。
- 确认 Windows 下可启动空 Textual 应用。

验收：

- `echoes` 命令能进入空白 TUI。
- `pytest` 通过。
- `ruff check` 通过。

### 阶段 1：SQLite 和迁移

目标：

- 建立 SQLite 连接层。
- 实现 schema 和迁移。
- 实现 words/cards/reviews/settings repository。

验收：

- 可创建数据库文件。
- 可插入词条和卡片。
- 复习日志事务测试通过。

### 阶段 2：三次掌握规则

目标：

- 实现 `pass_count` 状态。
- 实现 `next_review_turn` 延迟插队队列。
- 实现 Again/Hard/Easy 评分更新。
- 实现完成队列和批次进度统计。

验收：

- Easy 会推进 1 次。
- Hard 会降低 1 格。
- Again 清零。
- Again/Hard/Easy 会写入不同的下一次出现间隔。
- 3/3 后该词不再出现。

### 阶段 3：最小学习 UI

目标：

- 实现单词展示、答案展示、评分按键。
- 显示批次进度和当前词进度。
- 实现无卡片状态。

验收：

- 可完整复习一批卡片。
- 关闭再打开后状态保持。
- 未显示答案前评分无效。

### 阶段 4：Boss Key

目标：

- App 级快捷键切换学习/伪装视图。
- 实现假日志生成和滚动。
- 恢复学习状态。

验收：

- 任意界面按 Boss Key 都能立即切换。
- 再按一次能恢复原卡片和答案状态。
- 伪装日志连续滚动 10 分钟无异常。
- 切换不会写入复习记录。

### 阶段 5：导入和配置

目标：

- 支持 CSV 导入。
- 支持基础配置。
- 支持 `doctor` 检查。

验收：

- 能导入常见 CSV：`term,definition,phonetic,example,example_zh,tags`。
- 导入成功会完全覆盖旧数据，只保留本次 CSV 的 60 个有效词条。
- Boss Key 可配置。

### 阶段 6：打包和发布

目标：

- Windows 本地安装。
- 生成 Windows 便携版 zip。
- 完成基础 README。

验收：

- 新 Windows 环境解压 zip 后能双击脚本运行。
- 数据文件位置明确。
- 卸载不误删用户数据。

## 测试策略

必须测试：

- Again/Hard/Easy 的过关次数变化。
- Again/Hard/Easy 的下一次出现间隔。
- 3/3 后退出学习队列。
- SQLite 事务一致性。
- 未完成卡片查询排序：优先到期卡，再按进度和下一次出现位置排序。
- CSV 导入覆盖行为。
- Boss Key 状态切换。
- FakeLogService 行数上限。

可手动测试：

- Windows Terminal 中按键响应。
- PowerShell 启动。
- 长时间伪装日志滚动。
- 终端缩放和窗口大小变化。

测试约束：

- 单元测试不得依赖真实用户目录。
- 数据库测试使用临时目录。
- 时间相关测试使用固定时间或可注入时间。
- UI 测试优先测试状态机，不强行做复杂截图测试。

## 代码风格

- 代码使用类型标注。
- 业务逻辑尽量写成可测试的纯 Python 服务。
- UI 回调保持短小。
- 不在 UI 层直接访问 SQLite。
- 不在数据库层直接依赖 Textual。
- 不在核心逻辑中使用全局可变状态。
- 错误信息要短，不要在界面上暴露长 traceback，详细错误写入本地日志。
- 日志文件默认关闭或低噪声，避免暴露学习行为。

## 数据和隐私

- 所有学习数据默认只保存在本机。
- 不添加遥测。
- 不自动检查更新。
- 不联网拉取词典，除非用户显式启用。
- 导入新 CSV 时，旧词条、旧卡片和旧复习记录会被删除。
- 当前产品不保留历史词库，也不提供旧批次恢复。

## 未来增强想法

可考虑但不在 MVP 中强制实现：

- 多词库切换。
- 拼写练习卡。
- 仅英文释义模式。
- 每日上限和工作时段轻量提醒。
- Anki/CSV 导入。
- 伪装日志 profile 可自定义。
- 快速隐藏当前行的极简模式，而不是整屏切换。
- 可选浮动小窗不推荐，容易变显眼。

## 非目标

当前不做：

- FSRS 或跨天间隔重复调度。
- 云同步。
- 账号系统。
- Web 管理后台。
- 手机端。
- 浏览器插件。
- 企业监控绕过。
- 系统级热键监听。
- 进程名伪装。
- 自动截图规避。

## 给后续 Agent 的执行规则

在本仓库工作时：

- 先阅读本文件，再开发。
- 开发前确认用户是否只要计划还是要实现。
- 未经用户要求，不要开始项目代码开发。
- 若实现代码，保持 Windows 优先。
- 不要把 UI 做得像学习软件。
- Boss Key 相关改动必须优先保证状态恢复和不误写复习记录。
- 不要重新引入 FSRS，除非用户明确改变产品方向。
- 每次修改数据库 schema，都要同步迁移和测试。
- 最终总结要说重点，语句简明，不要长篇大论。
