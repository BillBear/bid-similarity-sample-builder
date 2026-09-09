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


## 三种构建模式

三种模式的核心差异不在于“是否生成样本”，而在于对文件结构理解、候选改造范围、语义复核深度和质量校验强度的不同。建议按文件复杂度、验收要求和可投入时间选择。

| 模式 | 工作方式 | 预计总耗时* | 优点 | 局限 | 适合场景 |
|---|---|---:|---|---|---|
| `fast` | 优先使用知识库中已配置的章节别名、字段标签和表格类型，自动筛选高置信候选；重点处理投标人名称、报价、地址、表格行等结构明确的内容。 | 单个受控样本通常为数分钟到数十分钟 | 速度快、成本低、结果稳定，适合批量构建。 | 对非标准目录、自拟章节、扫描件、复杂图片和低置信文本的覆盖较弱；容易集中在少数常见字段或章节。 | 文件结构稳定、格式相似、需要快速获得一批基础回归样本的项目。 |
| `balanced` | 在规则候选基础上，增加章节语义判断和跨文件匹配；覆盖关键字段、表格整行、图片及多个不同章节中的文本重复，并检查改造位置是否与正文语义一致。 | 单个受控样本通常为数十分钟到约 1 小时 | 质量、覆盖面和成本较均衡；能避免把无关内容硬插入正文，适合作为默认模式。 | 对特别长、图片密集或结构高度非标准的文件，仍可能遗漏低置信候选，需要人工抽查。 | 大多数常规投标文件；既要验证文本、字段、表格、图片等多类能力，又希望控制时间和成本的场景。 |
| `deep` | 先逐页梳理目录、章节边界和证据类型，再由语义判断选择对应章节进行替换；对文本改造会重点检查来源章节、主题一致性、替换长度档位和分布情况，并完成更严格的 Manifest、原值、改后值、位置及结果审计。 | 单个受控样本通常为 1–3 小时；超长文件、扫描件或图片较多时可能更久 | 覆盖最全面，文本改造更自然，能处理自拟方案、复杂承诺函、资质证明、图片附件和非标准章节；适合验收级样本。 | 时间和模型成本最高；不适合把大量文件全部采用该模式批量处理。 | 首次接入、产品验收、疑难文件、目录结构复杂或需要高质量文本重复样本的项目。 |

\* 预计总耗时指从文件解析、候选提取、语义分析、Manifest 生成、PDF 写入到校验报告完成的整体墙钟时间，不应只统计某个 PDF 写入脚本的运行秒数。实际耗时主要受页数、是否为扫描件、图片数量、表格复杂度、投标文件数量和人工复核要求影响。

### 选择建议

- 需要快速建立一批基础测试数据时，先使用 `fast`。
- 没有特别明确的限制时，优先使用 `balanced`，它是质量与成本之间的默认选择。
- 对外验收、复杂项目或发现 `balanced` 无法覆盖关键章节时，再使用 `deep`。
- 一个项目可以混用模式：大多数文件用 `fast` 或 `balanced`，挑选结构复杂、代表性强的文件用 `deep` 形成高质量标杆样本。
- 无论使用哪种模式，最终都应查看 Manifest、批注版 PDF 和验收报告，确认改造内容位于语义对应的原章节，而非通过插入无关文本制造重复。

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
