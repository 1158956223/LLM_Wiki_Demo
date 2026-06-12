# LLM Wiki 模块一：初始化能力实施计划

> **给 agentic worker 的要求：** 执行本计划时必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`。所有步骤使用 checkbox（`- [ ]`）追踪状态。

**目标：** 先交付第一个可独立测试的模块：Python 包骨架、路径/配置/状态/日志基础设施、DeepSeek 初始化内容生成、内置模板降级，以及交互式 `init` CLI 命令。

**架构：** CLI 入口保持很薄，只解析目标路径并询问项目名称与描述。确定性逻辑放在小模块中：`init` 负责创建项目目录结构、写入初始化内容、初始化配置/状态/搜索索引占位文件，并向 `wiki/log.md` 追加人类可读日志。DeepSeek 可用时生成 `purpose.md`、`schema.md` 和 `wiki/overview.md`；不可用时降级为内置模板。

**技术栈：** Python 标准库、`argparse`、`dataclasses`、`json`、轻量 TOML 读取逻辑、`unittest`、`langchain_openai.ChatOpenAI`。当前本机环境是 Python 3.10，因此不依赖 Python 3.11 才有的 `tomllib`。测试文件只用于本地验证，不随本模块提交上传。

---

## 模块边界

本模块只实现：

- 包入口：`src/llm_wiki/__init__.py`、`src/llm_wiki/__main__.py`、`src/llm_wiki/cli.py`
- 基础设施：`paths.py`、`config.py`、`state.py`、`log.py`、`errors.py`
- 模板与初始化行为：`templates.py`、`init.py`
- DeepSeek 初始化内容生成：`deepseek.py`，通过 LangChain 的 `ChatOpenAI` 调用 DeepSeek OpenAI-compatible API。
- 包配置：`pyproject.toml`
- 本地验证文件：`tests/test_cli.py`、`tests/test_init.py`、`tests/test_paths.py`、`tests/test_config_state_log.py`。这些文件只保留在本地，不提交到远端仓库。

本模块不实现 `ingest`、`search`、`query`、`proposal` 或 `lint`。这些命令在后续模块开始前可以暂时不存在。

### 任务 1：包结构与 CLI 入口

**文件：**
- 新建：`pyproject.toml`
- 新建：`src/llm_wiki/__init__.py`
- 新建：`src/llm_wiki/__main__.py`
- 新建：`src/llm_wiki/cli.py`
- 测试：`tests/test_cli.py`

- [x] **步骤 1：先写失败的 CLI 测试**

```python
import unittest

from llm_wiki.cli import build_parser


class CliParserTests(unittest.TestCase):
    def test_parser_accepts_init_path(self):
        args = build_parser().parse_args(["init", "--path", "D:/tmp/Demo"])

        self.assertEqual(args.command, "init")
        self.assertEqual(args.path, Path("D:/tmp/Demo"))

    def test_parser_rejects_removed_flags(self):
        parser = build_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(["init", "<旧的禁用 LLM 参数>"])
```

- [x] **步骤 2：运行测试确认失败**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_cli.py -v`

预期：失败，原因是 `llm_wiki` 包还不存在。

- [x] **步骤 3：实现最小包结构和解析器**

`pyproject.toml` 声明包元数据。`__main__.py` 调用 `cli.main()`。`cli.py` 暴露 `build_parser()` 和 `main()`，支持 `init --path`。其中 `--path` 表示初始化目标目录；不传 `--path` 时默认初始化当前工作目录。项目显示名称和项目描述通过交互式输入获得。

- [x] **步骤 4：运行测试确认通过**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_cli.py -v`

预期：通过。

### 任务 2：项目路径与安全路径解析

**文件：**
- 新建：`src/llm_wiki/errors.py`
- 新建：`src/llm_wiki/paths.py`
- 测试：`tests/test_paths.py`

- [x] **步骤 1：先写失败的路径测试**

```python
import unittest

from llm_wiki.errors import UnsafePathError
from llm_wiki.paths import ProjectPaths


class ProjectPathsTests(unittest.TestCase):
    def test_project_paths_expose_expected_locations(self):
        root = self._tmp_root()
        paths = ProjectPaths(root)

        self.assertEqual(paths.purpose, root / "purpose.md")
        self.assertEqual(paths.schema, root / "schema.md")
        self.assertEqual(paths.wiki_index, root / "wiki" / "index.md")
        self.assertEqual(paths.wiki_log, root / "wiki" / "log.md")
        self.assertEqual(paths.state, root / ".llm-wiki" / "state.json")
        self.assertEqual(paths.search_index, root / ".llm-wiki" / "search.sqlite")

    def test_safe_relative_rejects_path_escape(self):
        paths = ProjectPaths(self._tmp_root())

        with self.assertRaises(UnsafePathError):
            paths.safe_relative("../outside.md")
```

- [x] **步骤 2：运行测试确认失败**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_paths.py -v`

预期：失败，原因是路径和异常模块还不存在。

- [x] **步骤 3：实现异常类型和 `ProjectPaths`**

`ProjectPaths` 保存绝对项目根目录，暴露常用路径，并校验项目内相对路径不能逃逸到根目录外。

- [x] **步骤 4：运行测试确认通过**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_paths.py -v`

预期：通过。

### 任务 3：配置、状态与日志基础件

**文件：**
- 新建：`src/llm_wiki/config.py`
- 新建：`src/llm_wiki/state.py`
- 新建：`src/llm_wiki/log.py`
- 测试：`tests/test_config_state_log.py`

- [x] **步骤 1：先写失败的基础件测试**

```python
import json
import unittest

from llm_wiki.config import DEFAULT_CONFIG, load_config, write_default_config
from llm_wiki.log import append_log
from llm_wiki.paths import ProjectPaths
from llm_wiki.state import load_state, write_initial_state
```

- [x] **步骤 2：运行测试确认失败**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_config_state_log.py -v`

预期：失败，原因是配置、状态和日志模块还不存在。

- [x] **步骤 3：实现基础件**

配置使用 dataclass 表达各配置段；默认配置写入 `.llm-wiki/config.toml`，不包含 API Key；读取配置使用项目内轻量 TOML 解析器，兼容 Python 3.10。状态文件使用稳定 JSON 格式写入。日志追加为 Markdown 列表，包含本地时区时间戳和字段列表。

- [x] **步骤 4：运行测试确认通过**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_config_state_log.py -v`

预期：通过。

### 任务 4：模板、DeepSeek 与交互式 `init` 命令

**文件：**
- 新建：`src/llm_wiki/templates.py`
- 新建：`src/llm_wiki/init.py`
- 新建：`src/llm_wiki/deepseek.py`
- 修改：`src/llm_wiki/cli.py`
- 测试：`tests/test_init.py`

- [x] **步骤 1：先写失败的初始化测试**

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from llm_wiki.init import initialize_project
```

- [x] **步骤 2：运行测试确认失败**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_init.py -v`

预期：失败，原因是 `llm_wiki.init` 还不存在。

- [x] **步骤 3：实现模板与初始化逻辑**

创建目录树，写入带 marker 的模板文件，创建 `config.toml`、`state.json` 和空的 `search.sqlite` 占位文件，追加 init 日志，并返回 `InitResult`，其中包含 created、skipped 和 warnings。

- [x] **步骤 4：把 CLI 接到 `initialize_project`**

`python -m llm_wiki init --path "D:\tmp\我的 Wiki"` 应该先询问项目名称和描述，再创建目标目录并把 wiki 文件写入该目录。初始化默认尝试读取 `DEEPSEEK_API_KEY` 并调用 DeepSeek 生成 `purpose.md`、`schema.md` 和 `wiki/overview.md`；如果 API Key 缺失或调用失败，命令不中断，降级使用内置模板。旧的 LLM 禁用参数和覆盖参数不再提供。

- [x] **步骤 5：运行相关测试**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py" -v`

预期：已完成的模块一测试全部通过。

### 任务 5：模块验收

**文件：**
- 不新增文件。

- [x] **步骤 1：运行模块完整测试**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py" -v`

预期：全部测试通过。

- [x] **步骤 2：在临时目录运行 CLI 冒烟测试**

运行：`python -m llm_wiki init --path "<临时目录>\Smoke Wiki"`，并按提示输入项目名称和项目描述。

预期：命令退出码为 0，并在临时目录中创建设计文档规定的目录结构。

- [x] **步骤 3：检查 Git diff 范围**

运行：`git diff --stat`

预期：只包含模块一相关文件和本计划文档。
