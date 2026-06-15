# LLM Wiki 模块二：Ingest 实施计划

> **给 agentic worker 的要求：** 执行本计划时必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，并按任务逐步执行。所有步骤使用 checkbox（`- [ ]`）追踪状态。

**目标：** 交付第一条可用的摄入路径：用户传入一个项目外部的 Markdown 文件路径，工具先把它复制到项目内 `raw/sources/` 作为证据层，再生成 `wiki/sources/` 下的 source 页面，记录文件 hash 到状态文件，更新 `wiki/index.md`，并追加人类可读日志。

**架构：** CLI 保持很薄，只负责解析 `ingest <source>` 并调用业务函数。确定性的摄入逻辑放在 `src/llm_wiki/ingest.py`：校验输入必须是项目外部 `.md` 文件，复制到 `raw/sources/`，用 hash 检查是否重复导入，按固定模板创建 source wiki 页面，通过 `state.py` 更新 JSON 状态，并只更新 `wiki/index.md` 的来源列表。

**技术栈：** Python 标准库、`argparse`、`dataclasses`、`hashlib`、`json`、`unittest`。

---

## 文件结构

- 新建 `src/llm_wiki/ingest.py`：负责外部 source 路径校验、复制到 `raw/sources/`、重复 hash 检查、source 页面生成、状态更新、索引更新和日志记录。
- 修改 `src/llm_wiki/cli.py`：新增 `ingest [--path <项目目录>] <source>` 命令，并调用 `ingest_source`。
- 修改 `src/llm_wiki/state.py`：新增 `write_state`，用于稳定写回 JSON。
- 修改 `src/llm_wiki/errors.py`：确认或新增 `ProjectNotInitializedError`，并新增 `DuplicateSourceError`。
- 新建 `tests/test_ingest.py`：覆盖 ingest 行为和 CLI 解析。

### 任务 1：Source 摄入核心

**文件：**
- 新建：`src/llm_wiki/ingest.py`
- 修改：`src/llm_wiki/state.py`
- 修改：`src/llm_wiki/errors.py`
- 测试：`tests/test_ingest.py`

- [ ] **步骤 1：先写失败测试**

```python
def test_ingest_copies_external_source_then_creates_source_page_and_updates_state(self):
    workspace = self._tmp_root()
    root = self._initialized_project(workspace / "wiki_project")
    source = workspace / "external" / "example.md"
    source.parent.mkdir()
    source.write_text("# Example\n\nA useful note.\n", encoding="utf-8")

    result = ingest_source(root, source, summary_generator=self._summary)

    self.assertEqual(result.source_path, "raw/sources/example.md")
    self.assertEqual(result.wiki_page, "wiki/sources/example.md")
    self.assertTrue((root / "raw" / "sources" / "example.md").exists())
    self.assertIn("wiki/sources/example.md", (root / "wiki" / "index.md").read_text(encoding="utf-8"))
    self.assertIn("Example", (root / "wiki" / "sources" / "example.md").read_text(encoding="utf-8"))
```

- [ ] **步骤 2：运行测试，确认失败**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_ingest.py -v`

预期：失败，原因是 `llm_wiki.ingest` 还不存在。

- [ ] **步骤 3：实现最小代码**

实现 `IngestResult`、`ingest_source`、外部文件复制、`write_state` 和初始化状态检查。摘要生成函数保持可注入，确保单元测试不会调用 DeepSeek。

- [ ] **步骤 4：运行测试，确认通过**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_ingest.py -v`

预期：通过。

### 任务 2：安全性与幂等性

**文件：**
- 修改：`src/llm_wiki/ingest.py`
- 测试：`tests/test_ingest.py`

- [ ] **步骤 1：先写失败测试**

覆盖四类行为：拒绝项目内路径、拒绝非 Markdown 文件、拒绝已导入过的相同内容、外部文件与 `raw/sources/` 内已有文件同名但内容不同时向用户确认。

- [ ] **步骤 2：运行测试，确认失败**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_ingest.py -v`

预期：失败，原因是外部导入校验、重复导入检查和尚未实现。

- [ ] **步骤 3：实现校验与幂等**

解析用户输入的外部路径并要求它位于项目目录之外；要求文件扩展名为 `.md`；复制到 `raw/sources/<原文件名>`；复制前用 sha256 和 `state.json.sources` 检查重复内容；如果目标文件已存在且内容不同，CLI 向用户确认，确认后直接覆盖 `raw/sources/<原文件名>`，并基于新内容重新生成对应 source 页面、更新状态 hash、更新索引和日志。

- [ ] **步骤 4：运行测试，确认通过**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_ingest.py -v`

预期：通过。

### 任务 3：CLI 接入

**文件：**
- 修改：`src/llm_wiki/cli.py`
- 测试：`tests/test_ingest.py`

- [ ] **步骤 1：先写失败的 CLI 测试**

断言 `build_parser().parse_args(["ingest", "D:/notes/example.md"])` 能正确解析 source 路径；断言 `build_parser().parse_args(["ingest", "--path", "TestDemo", "D:/notes/example.md"])` 能正确解析项目目录；断言 `main([...], cwd=root, ingest_summary_generator=...)` 返回 0。

- [ ] **步骤 2：运行测试，确认失败**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_ingest.py -v`

预期：失败，原因是 CLI 还没有 `ingest` 命令。

- [ ] **步骤 3：新增 CLI 命令**

新增 `ingest` subparser，支持可选 `--path` 指向已初始化项目目录，并把命令路由到 `ingest_source`。如果用户在项目父目录或 `src` 目录中操作，可以使用 `--path TestDemo` 明确目标项目。

- [ ] **步骤 4：运行模块测试和完整测试**

运行：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py" -v`

预期：全部测试通过。
