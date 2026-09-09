# Bid Similarity Sample Builder

面向投标文件相似性检测的受控样本构建 Skill。它将文件结构理解、候选筛选、Manifest 校验和 PDF 写入分层，帮助测试文本重复、关键字段一致、表格行重复和图片重复能力。

它可与 [BidDupliCheck](https://github.com/BillBear/BidDupliCheck) 配合：本项目生成可审计的测试集，BidDupliCheck 运行查重并验证检出结果。

## 安装

```bash
git clone https://github.com/BillBear/bid-similarity-sample-builder.git
cd bid-similarity-sample-builder
python -m pip install -r requirements.txt
```

也可通过 skills.sh 安装：

```bash
npx skills add https://github.com/BillBear/bid-similarity-sample-builder
```

## 快速流程

```bash
python scripts/extract_candidates.py --pdf input/base.pdf --knowledge knowledge/defaults --out work/base.evidence.json
python scripts/extract_candidates.py --pdf input/controlled.pdf --knowledge knowledge/defaults --out work/controlled.evidence.json
python scripts/build_review_queue.py --base work/base.evidence.json --target work/controlled.evidence.json --knowledge knowledge/defaults --out work/review-queue.json
python scripts/validate_manifest.py work/manifest.json --knowledge knowledge/defaults
python scripts/apply_manifest.py --manifest work/manifest.json --knowledge knowledge/defaults --out output/controlled-sample.pdf --annotate
```

执行器生成 PDF 和同名 `.receipt.json`。中文写入使用 `--font` 或 `BID_SAMPLE_FONT_PATH` 指定字体；脚本也会查找常见系统中文字体。

## 工作方式

```text
投标 PDF → 只读证据包 → 候选审阅队列 → Agent Manifest → 校验 → 受控 PDF + 收据
```

| 层 | 负责内容 |
| --- | --- |
| Agent | 章节语义、跨文件配对、完整值确认、改造理由和 Manifest |
| 知识库 | 章节别名、字段标签、表格结构、文本来源规则 |
| 脚本 | 候选提取、排序、冲突校验、局部写入、批注和收据 |

详细流程见 [SKILL.md](SKILL.md)，字段定义见 [Manifest 合约](references/manifest-contract.md)。

## 三种模式

| 模式 | 特点 |
| --- | --- |
| `fast` | 针对高置信、已配置章节的候选，适合结构稳定的文件 |
| `balanced` | 复核文本、表格和复杂字段，适合常规样本构建 |
| `deep` | 逐页审阅复杂结构与低置信候选，适合验收级样本 |

## 配置知识库

默认规则位于 `knowledge/defaults`。通过项目 YAML 覆盖同名 `id`，即可扩展章节别名、字段标签和表格类型。

```yaml
schema_version: 1
sections:
  - id: after-sales-service
    aliases: [项目售后保障安排]
```

示例见 [examples/project-overrides/sections.yml](examples/project-overrides/sections.yml)。

## 数据处理

使用者应确认其拥有处理输入文件的授权，并在样本构建、验收和共享环节遵循适用的数据保护要求。仓库包含通用源码、配置和虚构示例。

## 开发验证

```bash
python -m pytest -q
python scripts/audit_release.py .
```

## 许可证

[Apache-2.0](LICENSE)
