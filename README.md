# zotero-skills

面向 AI Coding Agent（如 Claude Code, Cursor, Windsurf, Copilot, Cline 等）的本地 Zotero 文献库科研助手 Skill。

基于 Zotero Desktop 官方 Local API (`http://127.0.0.1:23119/api/`)，通过原生 Python 脚本实现本地文献检索、PDF 研读、高亮笔记提取、自动打标归档、格式化引文导出与文库体检。

## 特性

- **纯本地与隐私保护**：所有操作直连本机运行中的 Zotero Desktop，零云端中转，学术数据不出本地。
- **两阶段安全写入**：新建/修改标签、写入笔记、附件绑定均默认生成 Plan，用户确认后才执行 `--apply`。
- **Token 紧凑优化**：元数据检索与条目详情默认以科研核心精简格式返回，节省 Agent 上下文窗口。
- **客户端一键直达**：回答与引用文献均附带桌面深链接（`zotero://select/library/items/<key>` 及 `zotero://open-pdf/...`），随时点击跳转。
- **零额外依赖**：全套脚本基于 Python 标准库编写，无需额外 `pip install`。

---

## 一键安装

本项目完全兼容 [vercel-labs/skills](https://github.com/vercel-labs/skills) 规范。

### 1. 安装至当前项目

在您的代码或论文项目根目录下运行：

```bash
npx skills add kearril/zotero-skills
```

*(如果从完整 GitHub 地址安装：`npx skills add https://github.com/kearril/zotero-skills`)*

### 2. 全局安装（所有项目通用）

```bash
npx skills add -g kearril/zotero-skills
```

### 3. 指定目标 Agent 安装

```bash
# 例如指定为 Claude Code、Cursor 或全部 Agent 安装
npx skills add <owner>/zotero-skills --agent claude
npx skills add <owner>/zotero-skills --agent cursor
npx skills add <owner>/zotero-skills --agent '*'
```

---

## 前置要求

1. **Zotero Desktop**：保持 Zotero 客户端在后台运行。
2. **启用 Local API**：Zotero 默认开启本地 API（端口 `23119`）。
3. **Python 3.8+**：系统具备 Python 执行环境。

---

## 快速连通性验证

安装完成后，运行自检探针确认服务状态：

```bash
python .agents/skills/zotero-skills/scripts/zotero_check.py --json
```

若返回 `{"ok": true, ...}` 即表示与本地 Zotero 成功连接。

---

## 功能一览

| 模块        | 核心能力                                  | 对应脚本                     |
| --------- | ------------------------------------- | ------------------------ |
| **搜索与筛选** | 标题、作者、标签、分类及 PDF 全文索引检索               | `zotero_search.py`       |
| **阅读与提取** | 结构化元数据、核心摘要、分块全文及本地 PDF 路径            | `zotero_reading.py`      |
| **笔记与批注** | 提取 PDF 高亮与划线、生成富文本研读总结笔记              | `zotero_notes.py`        |
| **标签与分类** | 规划/应用标签增删、分类目录移动与层级管理                 | `zotero_organization.py` |
| **引文与导出** | 导出 BibTeX、CSL-JSON、RIS、APA、IEEE 格式化文本 | `zotero_citation.py`     |
| **录入与附件** | 本地 JSON 元数据新建条目、安全绑定上传 PDF 文件         | `zotero_ingest.py`       |
| **审计与体检** | 查重筛选、关键字段（DOI/摘要/PDF）缺失审计、增量追踪        | `zotero_maintenance.py`  |

---

## 开源协议

MIT
