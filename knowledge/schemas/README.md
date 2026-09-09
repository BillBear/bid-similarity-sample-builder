# 知识库格式

每个知识库 YAML 的顶层字段为 `schema_version: 1`。

- `sections.yml`：`id`、`title`、`role`、`aliases`、`text_allowed`
- `fields.yml`：`id`、`labels`
- `tables.yml`：`id`、`aliases`、`key_columns`
- `tender-bid-relations.yml`：`tender_role`、`allowed_bid_roles`、`use`
- `exclusions.yml`：文本来源角色和词项规则

加载时若两个章节将同一别名映射到不同 `id`，知识库会给出冲突错误，维护者可通过调整覆盖文件消解。
