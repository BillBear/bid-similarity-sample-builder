# Manifest 合约 v1

Manifest 是 Agent 的可审计改造决策。每个改造点都包含 `id`、`type`、`pair_id`、`semantic_reason`、`confidence`、`operation`，以及基准与受控两侧的 `file`、从 1 开始的 `page`、四数 `bbox`、`full_context`。

```json
{
  "schema_version": 1,
  "mode": "balanced",
  "knowledge": {"effective_config_hash": "<sha256>"},
  "documents": {"base": "base.pdf", "target": "target.pdf"},
  "points": []
}
```

| 类型 | operation | 关键字段 |
| --- | --- | --- |
| `FIELD` | `replace-existing-field` | `field_id`、`anchor_label`、`old_value`、`new_value`、`value_span_complete: true` |
| `TEXT` | `replace-existing-text` | `section_id`、`source_section_id`、`old_text`、`new_text` |
| `ROW` | `replace-table-cells` | `table_id`、`header_mapping`、`row_anchor`、`editable_columns`、`cells[]` |
| `IMG` | `replace-existing-image` | `source_image_hash`、`target_slot_description`、`replacement_image` |

`bbox` 使用 `[x0, y0, x1, y1]`。字段原值应完整出现在 `target.full_context` 中；文本点的 `section_id` 与 `source_section_id` 保持一致；表格单元格分别记录 bbox、原值和新值。Fast 模式的每个点附带 `confidence >= 0.90` 和 `auto_eligible: true`。
