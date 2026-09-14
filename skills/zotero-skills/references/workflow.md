# 科研工作流协同指南

用于需要跨多个环节的连续科研任务（如“检索文献 → 阅读精读 → 提炼笔记 → 打标归档 → 导出引文”）。

## 完整执行链路

```text
1. 连通性自检   zotero_check.py
2. 检索定位     zotero_search.py search
3. 深入精读     zotero_reading.py get / fulltext
4. 笔记提炼     zotero_notes.py create (先 plan)
5. 标签与归类   zotero_organization.py plan
6. [用户确认]   向用户展示拟写入的笔记内容与分类标签差异
7. 安全写入     zotero_notes.py create --apply && zotero_organization.py apply
8. 引文导出     zotero_citation.py export --keys KEY1,KEY2
```

## 各阶段协同规范

### 1. 检索与初筛
- 依据研究课题调用 `zotero_search.py` 获取候选清单。
- 向用户汇报检索结果时，每一篇文献均须提供：**完整论文标题**、**发表年份**、**作者简写**及**桌面端直达链接**（`zotero://select/library/items/<key>`）。

### 2. 深入精读与提炼
- 针对选定的核心论文，先使用 `zotero_reading.py get` 获取紧凑元数据和摘要。
- 若需要细读实验方法或数据，调用 `fulltext` 配合 `--offset` 分段读取正文。
- 引用具体实验或图表时，可提供 PDF 页码直达链接（`zotero://open-pdf/library/items/<attachment_key>?page=<page>`）。

### 3. 笔记与归纳
- 提炼核心学术要点（学术痛点、创新构型/算法、实验对比数据、课题启发）。
- 调用 `zotero_notes.py create` 生成 Plan，输出拟创建的富文本笔记大纲。

### 4. 标签归档与用户审批（关键节点）
- 根据文献主题制定标签增删计划（如添加 `Status/Read`、`Topic/AI`）。
- 整合【笔记内容】与【标签归档 Plan】，向用户统一发出确认申请。
- **用户确认前，严禁调用带有 `--apply` 的写命令。**

### 5. 执行写入与导出
- 用户批准后，依次带 `--apply` 参数执行笔记写入与标签修改，并根据返回结果确认版本一致性。
- 若用户需要论文引用，调用 `zotero_citation.py export` 导出指定格式（如 BibTeX 或 GB/T 7714）。
