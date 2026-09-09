---
name: bid-similarity-sample-builder
description: 基于可配置知识库和可审计 Manifest 构造投标文件相似性检测样本，覆盖文本、关键字段、表格行和图片改造。
---

# 标书相似性样本构建器

本 Skill 采用“Agent 语义决策 + 脚本确定性执行”的流程。Agent 阅读文件结构、确认同类章节和完整原值，再签发 Manifest；脚本提取候选、校验 Manifest、写入 PDF 并生成收据。

## 输入准备

1. 准备招标文件和两份或多份投标 PDF；招标文件用于理解项目结构和响应关系。
2. 盘点每份投标文件的目录、章节、字段、表格、图片和可编辑文本层。
3. 加载 `knowledge/defaults`，按需增加项目覆盖 YAML。

## 三种模式

| 模式 | 适用场景 | 执行要求 |
| --- | --- | --- |
| `fast` | 结构清晰、候选高置信的文件 | 置信度至少 0.90，并标记 `auto_eligible: true` |
| `balanced` | 常规项目 | Agent 复核文本、表格、复杂字段与异常点 |
| `deep` | 目录差异大、页面复杂或质量要求高的文件 | Agent 审核全部候选及页面证据 |

## 语义决策标准

- 文本点在双方同一投标人自拟章节内完成原文替换。每份受控文件覆盖至少 5 个文本点，并覆盖 10–50、50–150、150–300 字长度档。
- 关键字段定位到页面既有标签后的完整值，记录标签、上下文、原值、新值和 bbox。
- 表格点以逻辑行和既有单元格为边界，记录表头映射、行锚点、可变列及每个单元格的新旧值和 bbox。
- 图片点定位到既有图片槽位，记录来源图片哈希、受控槽位说明和替换图片路径。
- 同一页面的可编辑区域保持互不重叠；每个点都附带可复核的章节和页面证据。

## 工作流

1. 运行 `extract_candidates.py`，生成只读证据包。
2. 使用 `build_review_queue.py` 汇总同章节候选，完成 Agent 复核。
3. 依据 `references/manifest-contract.md` 编写 Manifest。
4. 运行 `validate_manifest.py`，修正全部校验问题。
5. 运行 `apply_manifest.py` 生成受控 PDF、JSON 收据；按需使用 `--annotate` 生成标注版。
6. 抽查所有测试点的章节相关性、字段完整性、表格列对齐、图片槽位和批注。

## 知识库

- `knowledge/defaults/sections.yml`：章节族、别名、角色和文本适用性。
- `knowledge/defaults/fields.yml`：字段语义和标签别名。
- `knowledge/defaults/tables.yml`：表格类别和关键列。
- `knowledge/defaults/tender-bid-relations.yml`：招标与投标的结构关系。
- `knowledge/defaults/exclusions.yml`：章节角色和词项的文本来源规则。

项目覆盖文件通过相同 `id` 扩展别名或覆盖属性。知识库加载会计算 `effective_config_hash`，将该值写入 Manifest 的 `knowledge` 节点。
