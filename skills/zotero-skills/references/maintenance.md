# 文献库维护与体检审计指南

用于筛查文献库中的残缺条目（缺 DOI、缺摘要、缺 PDF）、发现重复文献候选，以及追踪本地增量变更。

## 常用命令

```bash
# 1. 快速体检（默认检查缺少 DOI、缺少摘要的条目）
python <skill_dir>/scripts/zotero_maintenance.py audit --limit 100 --json

# 2. 全面健康审计：严格检查缺少 DOI、摘要、缺少本地 PDF 附件并检测疑似重复条目
python <skill_dir>/scripts/zotero_maintenance.py audit \
  --require DOI \
  --require abstractNote \
  --require-pdf \
  --duplicates \
  --limit 200 \
  --json

# 3. 追踪自特定版本号（version）以来的文献条目增量变更
python <skill_dir>/scripts/zotero_maintenance.py changes --since 100 --kind items --json

# 4. 追踪全文索引的增量变更
python <skill_dir>/scripts/zotero_maintenance.py changes --since 100 --kind fulltext --json
```
## 执行规范

1. **只读诊断，严禁擅自修改**：
   - 审计脚本为纯只读诊断，只输出统计数据和问题文献清单，绝不擅自删除、覆盖或合并任何条目。
2. **重复文献去重流程**：
   - 发现重复候选时，提取两篇文献的标题、年份、作者与桌面链接（`zotero://select/library/items/<key>`），汇总呈现给用户。
   - 只有在用户明确指示保留某篇并清理另一篇时，才转至 `organization` 流程安全处理。
3. **缺陷文献报告**：
   - 向用户汇报缺失关键信息的条目时，必须列出文献标题与直达链接，便于用户核实或手动补齐。
