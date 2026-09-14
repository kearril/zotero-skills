# 文献搜索与筛选指南

用于按关键词、作者、年份、标签、分类集合或全文索引快速定位文献。

## 常用命令

```bash
# 1. 基础标题与作者搜索
python <skill_dir>/scripts/zotero_search.py search --q "deep learning" --limit 20 --json

# 2. 全文索引检索（需 Zotero 本地已建立 PDF 全文索引）
python <skill_dir>/scripts/zotero_search.py search --q "transformer" --qmode everything --item-type journalArticle --json

# 3. 按指定标签检索（支持多个 --tag）
python <skill_dir>/scripts/zotero_search.py search --tag "Topic/AI" --tag "Status/Read" --json

# 4. 查看指定分类目录下的文献
python <skill_dir>/scripts/zotero_search.py search --collection-key COLL_KEY --limit 50 --json

# 5. 查看所有分类目录与层级结构
python <skill_dir>/scripts/zotero_search.py collections --top --json

# 6. 查询已保存的搜索视图（Saved Searches）
python <skill_dir>/scripts/zotero_search.py searches --json
```

## 参数说明

- `--q <query>`：搜索关键词。
- `--qmode <mode>`：匹配模式，可选 `titleCreatorYear`（默认，快速匹配标题/作者/年份）或 `everything`（含全文与笔记内容）。
- `--item-type <type>`：文献类型，如 `journalArticle`、`book`、`conferencePaper`。
- `--tag <tag>`：按标签过滤，可重复传入表示“且”关系。
- `--collection-key <key>`（别名 `--collection`）：限定在特定分类集合中。
- `--item-key <key>`（别名 `--key`）：直接按条目 Key 获取（支持逗号分隔多个）。
- `--limit <n>`：返回数量，默认 20，最大 100。
- `--start <n>`：翻页偏移量。

## 结果处理规范

1. **结果呈现**：输出包含条目 Key、标题、作者、年份、类型、标签与 `zotero_uri`。
2. **向用户展示**：向用户展示检索结果时，必须附带论文完整标题与桌面端直达链接（`zotero://select/library/items/<key>`）。
3. **深入研读**：搜索仅用于筛选候选；深入阅读与分析请将选定的 Key 传递给 `zotero_reading.py`。
