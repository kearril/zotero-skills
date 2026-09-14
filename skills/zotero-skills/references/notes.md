# 笔记与批注管理指南

用于读取文献下的高亮批注、提炼文献研读总结并写回 Zotero 笔记。

## 常用命令

```bash
# 1. 查看文献下的所有笔记与 PDF 划线批注
python <skill_dir>/scripts/zotero_notes.py list ITEM_KEY --kind all --json
# 仅筛选批注（划线高亮）：
python <skill_dir>/scripts/zotero_notes.py list ITEM_KEY --kind annotation --json
# 仅筛选独立笔记：
python <skill_dir>/scripts/zotero_notes.py list ITEM_KEY --kind note --json

# 2. 读取特定笔记或批注的详细内容
python <skill_dir>/scripts/zotero_notes.py get NOTE_KEY --json

# 3. 规划创建文献研读笔记（预览 Plan，不真正写入）
python <skill_dir>/scripts/zotero_notes.py create --parent ITEM_KEY --title "Literature Summary" --body "<p>Core Contribution: ...</p>" --json

# 4. 执行创建笔记（必须经用户确认后带 --apply 执行）
python <skill_dir>/scripts/zotero_notes.py create --parent ITEM_KEY --title "Literature Summary" --body "<p>Core Contribution: ...</p>" --apply --json

# 5. 更新已有笔记内容
python <skill_dir>/scripts/zotero_notes.py update NOTE_KEY --body "<p>Updated Analysis: ...</p>" --version 123 --apply --json
```
## 交互规范与两阶段写入

1. **写操作两阶段安全门**：
   - 任何新建笔记或更新笔记操作，必须先向用户展示待生成的笔记标题、结构化大纲与正文内容。
   - 用户明确确认后，再带 `--apply` 参数执行写入。
2. **笔记内容结构建议**：
   Agent 撰写科研笔记时，优先采用清晰的结构化 HTML 标签，建议包含：
   - **核心问题与背景**：论文解决的核心学术/工程痛点。
   - **创新方法与构型**：采用的核心算法、传感器构型或实验方案。
   - **关键指标与结果**：关键实验数据、提升幅度或定量结论。
   - **局限性与启发**：本文限制以及对当前研究课题的具体启发。
3. **关联跳转**：
   汇报已生成的笔记时，附带父级文献的桌面直达链接 `zotero://select/library/items/<parent_key>`。
