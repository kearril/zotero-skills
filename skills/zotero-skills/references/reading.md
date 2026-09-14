# 文献研读与内容读取指南

用于读取文献条目的结构化元数据、子附件信息、PDF 正文片段与本地文件路径。

## 常用命令

```bash
# 1. 读取文献核心元数据（默认紧凑模式，提取核心科研字段）
python <skill_dir>/scripts/zotero_reading.py get ITEM_KEY --json
# 亦支持 --key 参数：
python <skill_dir>/scripts/zotero_reading.py get --key ITEM_KEY --json

# 2. 读取完整原始结构（调试或需底层 Schema 时使用）
python <skill_dir>/scripts/zotero_reading.py get ITEM_KEY --raw --json

# 3. 列出文献的所有子项（包含附件 PDF、笔记 Note、高亮批注 Annotation）
python <skill_dir>/scripts/zotero_reading.py children ITEM_KEY --json

# 4. 分块读取 PDF 全文索引内容（默认 8000 字符，按需分段推进）
python <skill_dir>/scripts/zotero_reading.py fulltext ATTACHMENT_KEY --offset 0 --limit 8000 --json

# 5. 获取本地 PDF 附件真实文件路径（需配置本地存储目录）
python <skill_dir>/scripts/zotero_reading.py path ATTACHMENT_KEY --json
```

## 执行规范

1. **Token 紧凑输出**：
   - `get` 命令默认仅提取科研关心的关键字段（标题、作者、年份、DOI、摘要、标签、分类、附件列表及直达深链接），极大节省上下文开销。
2. **全文有界读取**：
   - 不一次性将长篇论文全文读入上下文；使用 `fulltext` 配合 `--offset` 与 `--limit` 逐段阅读。
   - 当 `has_more: true` 时，表示正文仍有未读完的内容，可通过调整 `--offset` 继续推进。
3. **文献展示与跳转**：
   - 向用户总结、解读或引用文献时，必须附带论文完整标题与桌面深链接：
     - 条目直达：`zotero://select/library/items/<item_key>`
     - 附件/页码直达：`zotero://open-pdf/library/items/<attachment_key>?page=<page>`
