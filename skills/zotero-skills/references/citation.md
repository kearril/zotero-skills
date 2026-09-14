# 引文格式化与导出指南

用于将选定的一组文献批量生成标准学术引用文本或导出指定格式的数据文件。

## 常用命令

```bash
# 1. 导出 BibTeX（支持多 key，逗号分隔）
python <skill_dir>/scripts/zotero_citation.py export --keys KEY1,KEY2 --format bibtex --json
# 亦支持单篇 --key：
python <skill_dir>/scripts/zotero_citation.py export --key KEY1 --format bibtex --json

# 2. 导出 CSL-JSON（常用于文献元数据程序化交换）
python <skill_dir>/scripts/zotero_citation.py export --keys KEY1,KEY2 --format csljson --json

# 3. 按指定期刊/国家标准格式化参考文献文本（如 APA、IEEE、GB/T 7714）
python <skill_dir>/scripts/zotero_citation.py export --keys KEY1,KEY2 --format bib --style apa --locale zh-CN --json

# 4. 导出为 RIS 文件并直接写入本地文件
python <skill_dir>/scripts/zotero_citation.py export --keys KEY1,KEY2 --format ris --output-file references.ris --json
```

## 支持格式

- **格式（`--format`）**：`bibtex`, `biblatex`, `bib` (文本条目), `csljson`, `ris`, `csv`, `mods`, `refer`, `tei`, `wikipedia`。
- **引用样式（`--style`）**：支持 Zotero 本地已安装的 CSL 样式名（如 `apa`, `ieee`, `nature`, `chinese-gb7714-2015-numeric` 等）。
- **语言区域（`--locale`）**：如 `zh-CN`, `en-US`。

## 交互规范

1. **确定文献清单**：导出前向用户明确文献范围（列出文献完整标题与条目深链接 `zotero://select/library/items/<key>`）。
2. **纯粹输出**：引文导出属于只读操作，不会改变 Zotero 库内条目内容；若带 `--output-file` 则仅在本地文件系统保存结果。
