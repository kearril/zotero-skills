# 标签与分类整理指南

用于批量管理文献标签、分配分类目录（Collection）、修改元数据字段与建立文献关联。

## 常用命令

```bash
# 1. 规划标签与分类调整（生成 Diff 预览方案，不写入）
python <skill_dir>/scripts/zotero_organization.py plan ITEM_KEY \
  --add-tag "Topic/AI" \
  --remove-tag "ToRead" \
  --add-collection COLL_KEY \
  --json

# 2. 执行标签与分类修改（必须在用户确认后执行，携带当前版本号）
python <skill_dir>/scripts/zotero_organization.py apply ITEM_KEY \
  --add-tag "Topic/AI" \
  --remove-tag "ToRead" \
  --version 120 \
  --json

# 3. 查看当前所有分类目录
python <skill_dir>/scripts/zotero_organization.py collections --json

# 4. 规划创建新分类目录（预览）
python <skill_dir>/scripts/zotero_organization.py create-collection "Survey Review" --parent-key PARENT_COLL_KEY --json

# 5. 执行创建分类目录
python <skill_dir>/scripts/zotero_organization.py create-collection "Survey Review" --apply --json
```
## 执行规则与安全保障

1. **先 Plan 后 Apply**：
   - 必须先调用 `plan`，获取变更前（`before`）与变更后（`after`）的字段差异和当前版本号（`version`）。
   - 向用户以表格或列表清晰展示拟变更内容。
2. **用户授权与版本互斥**：
   - 获得用户许可后，将 plan 输出的 `version` 传给 `apply --version`。
   - 若本地版本已被外部修改，系统将自动拒绝写入（触发版本保护），防止覆盖最新修改。
3. **保留未变更属性**：
   - 脚本采用局部合并机制，添加或移除标签时会自动保留原有其他标签与分类关系，不会误清空未提及的数据。
4. **文献呈现**：
   - 整理过程中提及文献时，需展示完整标题及 `zotero://select/library/items/<key>` 桌面直达链接。
