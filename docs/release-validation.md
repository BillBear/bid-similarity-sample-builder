# Release Validation

日期：2026-09-08

## 环境

- Python 3.12.7
- PyMuPDF、PyYAML、pytest

## 已验证项目

| 项目 | 结果 |
| --- | --- |
| 单元测试 | 18 passed |
| PDF 文本、图片、批注写入 | 通过合成 PDF 测试 |
| Manifest 完整值、区域冲突与失败路径 | 通过 |
| 知识库覆盖、候选排序、审阅队列 | 通过 |
| 命令行帮助入口 | 通过 |
| 虚构 Manifest 校验 | 通过 |
| 发布审计 | 通过 |

## 复现命令

```bash
python -m pytest -q
python scripts/validate_manifest.py examples/manifest.example.json --knowledge knowledge/defaults
python scripts/audit_release.py .
```
