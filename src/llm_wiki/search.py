from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .paths import ProjectPaths


@dataclass(frozen=True)
class SearchResult:
    path: str
    title: str
    type: str
    snippet: str  # 命中的文本片段
    score: float  # 匹配得分


def rebuild_search_index(root: str | Path) -> None:
    paths = ProjectPaths(Path(root))
    paths.search_index.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(paths.search_index)
    try:
        # 先删除旧表
        connection.execute("DROP TABLE IF EXISTS pages_fts")
        connection.execute("DROP TABLE IF EXISTS pages")

        # 创建page表，包括页面路径、标题、类型、内容
        connection.execute(
            "CREATE TABLE pages (path TEXT PRIMARY KEY, title TEXT NOT NULL, type TEXT NOT NULL, content TEXT NOT NULL)"
        )
        _create_fts_table(connection)
        for page in sorted(paths.wiki_dir.rglob("*.md")):
            rel_path = page.relative_to(paths.root).as_posix()
            text = page.read_text(encoding="utf-8")
            title = _title_from_wiki_page(page)
            page_type = _frontmatter_value(text, "type") or "unknown"
            row = (rel_path, title, page_type, text)

            # 写入两个表
            connection.execute("INSERT INTO pages(path, title, type, content) VALUES (?, ?, ?, ?)", row)
            connection.execute("INSERT INTO pages_fts(path, title, type, content) VALUES (?, ?, ?, ?)", row)
        connection.commit()
    finally:
        connection.close()


def search_pages(root: str | Path, query: str, *, top_k: int) -> list[SearchResult]:
    paths = ProjectPaths(Path(root))
    if not paths.search_index.exists():
        raise FileNotFoundError(paths.search_index)
    if not query.strip() or top_k <= 0:
        return []

    connection = sqlite3.connect(paths.search_index)
    try:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
              path,
              title,
              type,
              snippet(pages_fts, 3, '', '', '...', 18) AS snippet,
              bm25(pages_fts) AS score
            FROM pages_fts
            WHERE pages_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (_fts_query(query), top_k),
        ).fetchall()

        # 如果 FTS 没有结果,再用 LIKE 模糊搜索
        if not rows:
            rows = _like_search(connection, query, top_k)
    finally:
        connection.close()
    return [
        SearchResult(
            path=str(row["path"]),
            title=str(row["title"]),
            type=str(row["type"]),
            snippet=str(row["snippet"]),
            score=float(row["score"]),
        )
        for row in rows
    ]


# 创建索引表
def _create_fts_table(connection: sqlite3.Connection) -> None:
    try:
        # path 和 type 不参与全文索引
        connection.execute(
            "CREATE VIRTUAL TABLE pages_fts USING fts5(path UNINDEXED, title, type UNINDEXED, content, tokenize='trigram')"
        )
    except sqlite3.OperationalError:
        connection.execute(
            "CREATE VIRTUAL TABLE pages_fts USING fts5(path UNINDEXED, title, type UNINDEXED, content)"
        )


# 把用户输入变成 FTS 查询语句
def _fts_query(query: str) -> str:
    terms = _search_terms(query)
    if not terms:
        escaped = query.strip().replace('"', '""')
        return f'"{escaped}"'
    return " OR ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)


def _like_search(connection: sqlite3.Connection, query: str, top_k: int) -> list[sqlite3.Row]:
    terms = _search_terms(query)
    if not terms:
        return []
    clauses = " OR ".join(["lower(title) LIKE ? OR lower(content) LIKE ?" for _ in terms])
    params: list[str | int] = []
    for term in terms:
        pattern = f"%{term.lower()}%"
        params.extend([pattern, pattern])
    params.append(top_k)
    return connection.execute(
        f"""
        SELECT
          path,
          title,
          type,
          substr(content, 1, 240) AS snippet,
          0.0 AS score
        FROM pages
        WHERE {clauses}
        LIMIT ?
        """,
        params,
    ).fetchall()


# 从用户提问中提取关键字
def _search_terms(query: str) -> list[str]:
    normalized_query = _normalize_query_text(query)
    terms: list[str] = []
    for term in re.findall(r"[A-Za-z0-9]+", normalized_query, flags=re.UNICODE):
        normalized = term.strip().lower()
        if len(normalized) < 3:
            continue
        terms.append(term)

    chinese_text = "".join(re.findall(r"[\u4e00-\u9fff]+", normalized_query, flags=re.UNICODE))
    if chinese_text:
        for stopword in [
            "请问",
            "什么是",
            "是什么",
            "什么",
            "如何",
            "怎么",
            "为什么",
            "介绍一下",
            "解释一下",
            "说说",
        ]:
            chinese_text = chinese_text.replace(stopword, "")
        if len(chinese_text) >= 2:
            terms.append(chinese_text)
            if len(chinese_text) >= 3:
                terms.extend(chinese_text[index: index + 2] for index in range(len(chinese_text) - 1))
            if len(chinese_text) >= 4:
                terms.extend(chinese_text[index: index + 3] for index in range(len(chinese_text) - 2))

    return list(dict.fromkeys(terms))[:8]


def _normalize_query_text(query: str) -> str:
    text = re.sub(r"[_-]+", " ", query)
    text = re.sub(r"([\u4e00-\u9fff])([A-Za-z0-9])", r"\1 \2", text)
    text = re.sub(r"([A-Za-z0-9])([\u4e00-\u9fff])", r"\1 \2", text)
    return text


def _title_from_wiki_page(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^title:\s*(.+)$", text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"')
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ")


def _frontmatter_value(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip('"')
