# 文献录入与附件管理指南

用于根据结构化元数据新建文献条目，以及为已有文献关联并上传本地 PDF 附件。

## 常用命令

```bash
# 1. 规划新建文献条目（校验 JSON 结构与字段，预览 Plan）
python <skill_dir>/scripts/zotero_ingest.py create-item --type journalArticle --json-file item.json --json

# 2. 执行新建文献条目（用户确认后执行）
python <skill_dir>/scripts/zotero_ingest.py create-item --type journalArticle --json-file item.json --apply --json

# 3. 规划上传并关联本地 PDF 文件（计算哈希与大小，预览）
python <skill_dir>/scripts/zotero_ingest.py upload ATTACHMENT_KEY paper.pdf --json

# 4. 执行上传并替换已有附件文件（严格校验 MD5）
python <skill_dir>/scripts/zotero_ingest.py upload ATTACHMENT_KEY paper.pdf --replace --apply --json
```

## 执行规则与安全保障

1. **两阶段安全录入**：
   - 必须先运行 `create-item` 生成计划，校验文献类型（`itemType`）与元数据字段是否符合 Zotero 规范。
   - 向用户清晰展示拟录入文献的标题、作者、年份、期刊及 DOI，确认无误后再带 `--apply` 执行。
2. **安全文件上传**：
   - 上传过程自动进行 MD5 校验与完整性确认，防止附件传输损坏。
   - 若附件已有文件，默认不会静默覆盖，必须显式指定 `--replace`。
3. **完成反馈**：
   - 录入成功后，必须向用户展示新创建条目的完整标题与桌面直达链接：`zotero://select/library/items/<new_key>`。
