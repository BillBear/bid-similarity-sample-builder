"""Versioned, mergeable business knowledge for tender-document samples."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

import yaml


class KnowledgeBaseError(ValueError):
    """Raised when a user-editable knowledge file is malformed or ambiguous."""


CONFIG_NAMES = (
    "sections.yml",
    "fields.yml",
    "tables.yml",
    "tender-bid-relations.yml",
    "exclusions.yml",
)


def normalize(value: str) -> str:
    return re.sub(r"[\s\W_]+", "", value, flags=re.UNICODE).lower()


def heading_key(value: str) -> str:
    value = re.sub(
        r"^\s*(?:(?:第[一二三四五六七八九十百千万零〇\d]+[章节部分])|(?:[一二三四五六七八九十百千万零〇]+[、.．])|(?:\d+(?:\.\d+){0,4}[、.．]?))\s*",
        "",
        value,
    )
    return normalize(value)


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise KnowledgeBaseError(f"无法读取知识库文件 {path.name}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise KnowledgeBaseError(f"{path.name} 必须包含 schema_version: 1")
    return data


def _merge_records(base: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = [copy.deepcopy(item) for item in base]
    positions = {item.get("id"): index for index, item in enumerate(result) if item.get("id")}
    for incoming_item in incoming:
        identifier = incoming_item.get("id")
        if not identifier:
            raise KnowledgeBaseError("带 id 的知识库条目缺少 id")
        if incoming_item.get("disabled"):
            if identifier in positions:
                result.pop(positions[identifier])
                positions = {item.get("id"): index for index, item in enumerate(result) if item.get("id")}
            continue
        if identifier not in positions:
            result.append(copy.deepcopy(incoming_item))
            positions[identifier] = len(result) - 1
            continue
        existing = result[positions[identifier]]
        merged = copy.deepcopy(existing)
        for key, value in incoming_item.items():
            if key == "aliases" and value is not None:
                merged[key] = list(dict.fromkeys([*existing.get("aliases", []), *value]))
            elif key != "id":
                merged[key] = copy.deepcopy(value)
        result[positions[identifier]] = merged
    return result


class KnowledgeBase:
    def __init__(self, data: dict[str, Any], source_paths: Iterable[Path]):
        self.data = data
        self.source_paths = [str(path) for path in source_paths]
        canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.effective_config_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self._section_aliases: dict[str, dict[str, Any]] = {}
        for section in self.sections:
            for label in [section.get("title", ""), *section.get("aliases", [])]:
                key = normalize(label)
                if not key:
                    continue
                existing = self._section_aliases.get(key)
                if existing and existing["id"] != section["id"]:
                    raise KnowledgeBaseError(f"章节别名冲突：{label} 同时指向 {existing['id']} 和 {section['id']}")
                self._section_aliases[key] = section

    @property
    def sections(self) -> list[dict[str, Any]]:
        return self.data.get("sections", [])

    @classmethod
    def load(
        cls,
        default_dir: Path,
        *,
        pack_dirs: Iterable[Path] = (),
        override_files: Iterable[Path] = (),
    ) -> "KnowledgeBase":
        data: dict[str, Any] = {"sections": [], "fields": [], "tables": [], "relations": [], "exclusions": {}}
        source_paths: list[Path] = []

        def apply(path: Path) -> None:
            payload = _read_yaml(path)
            source_paths.append(path)
            if path.name == "sections.yml":
                data["sections"] = _merge_records(data["sections"], payload.get("sections", []))
            elif path.name == "fields.yml":
                data["fields"] = _merge_records(data["fields"], payload.get("fields", []))
            elif path.name == "tables.yml":
                data["tables"] = _merge_records(data["tables"], payload.get("tables", []))
            elif path.name == "tender-bid-relations.yml":
                data["relations"].extend(payload.get("relations", []))
            elif path.name == "exclusions.yml":
                data["exclusions"].update(payload)

        for directory in [Path(default_dir), *map(Path, pack_dirs)]:
            for name in CONFIG_NAMES:
                candidate = directory / name
                if candidate.exists():
                    apply(candidate)
        for override in map(Path, override_files):
            if not override.exists():
                raise KnowledgeBaseError(f"覆盖文件不存在：{override}")
            apply(override)
        return cls(data, source_paths)

    def classify_section(self, title: str) -> dict[str, Any] | None:
        return self._section_aliases.get(heading_key(title))

    def section(self, identifier: str) -> dict[str, Any] | None:
        return next((item for item in self.sections if item.get("id") == identifier), None)

    def field(self, identifier: str) -> dict[str, Any] | None:
        return next((item for item in self.data.get("fields", []) if item.get("id") == identifier), None)

    def field_has_label(self, identifier: str, label: str) -> bool:
        field = self.field(identifier)
        return bool(field and normalize(label) in {normalize(item) for item in field.get("labels", [])})

    def is_text_allowed(self, identifier: str) -> bool:
        section = self.section(identifier)
        prohibited = set(self.data.get("exclusions", {}).get("text_prohibited_roles", []))
        return bool(section and section.get("text_allowed") and section.get("role") not in prohibited)
