---
name: zotero-skills
description: Use when user mentions Zotero to search, read, inspect, organize, annotate, import, cite, export, audit, or maintain their local literature database.
---

# Zotero

本地 Zotero 桌面端操作入口。

## 执行顺序

1. **环境自检**：
   运行本地探针：
   
   ```bash
   python <skill_dir>/scripts/zotero_check.py --json
   ```
   
   检测失败则终止操作，提示用户确保 Zotero 客户端已启动且本地 API 处于监听状态。
2. **定向路由**：
   根据用户具体意图，**查阅下方【功能路由】中的对应参考文件**。
3. **数据调用**：
   依参考文件指示调用分类脚本，所有脚本均输出标准 JSON。
4. **两阶段安全写入**：
   任何新建、修改、删除或上传操作，**必须先输出清晰的 Plan 待用户确认**；用户明确许可后，方可携带 `--apply` 执行。

## 交互规范

- **文献展示**：讨论或汇报任何文献时，**必须同时提供完整论文标题**与**桌面端直达深链接**：
  - 条目直达：`zotero://select/library/items/<item_key>`
  - PDF 页码直达：`zotero://open-pdf/library/items/<attachment_key>?page=<page>`
- **Token 节约**：检索与详情读取默认采用紧凑模式，仅输出科研核心字段；非必要不调用 `--raw`。
- **并发保护**：更新条目或笔记必须传递版本号（`--version <version>`）；若返回 `412`（版本冲突），停止写入并重新拉取最新版本。

## 功能路由

| 用户意图                          | 参考文件                         | 对应脚本                     |
| ----------------------------- | ---------------------------- | ------------------------ |
| 搜索、作者/年份/标签筛选、全文查找            | `references/search.md`       | `zotero_search.py`       |
| 读取条目元数据、摘要、全文片段、本地文件路径        | `references/reading.md`      | `zotero_reading.py`      |
| 标签管理、分类调整、字段修改、关联关系           | `references/organization.md` | `zotero_organization.py` |
| 提取划线批注、创建/更新文献研读笔记            | `references/notes.md`        | `zotero_notes.py`        |
| 导出 BibTeX、CSL-JSON、RIS、格式化引文  | `references/citation.md`     | `zotero_citation.py`     |
| 录入本地文献条目、绑定上传 PDF 附件          | `references/ingest.md`       | `zotero_ingest.py`       |
| 库体检审计（缺 DOI/摘要/PDF）、查重、增量追踪   | `references/maintenance.md`  | `zotero_maintenance.py`  |
| “检索 → 研读 → 笔记 → 归类 → 引用”连续工作流 | `references/workflow.md`     | 多脚本联动                    |
