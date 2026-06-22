"""Validation and serialization for versioned project taxonomy configs."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Sequence


AXIS_RULES = {
    "issues": {"minimum": 5, "maximum": 10, "required": "lainnya"},
    "stances": {"minimum": 3, "maximum": 8, "required": "tidak_terdeteksi"},
    "actions": {"minimum": 4, "maximum": 8, "required": "tidak_terdeteksi"},
}


def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")


def parse_labels(value: Any) -> List[Dict[str, Any]]:
    """Parse structured JSON labels and tolerate legacy comma-separated keys."""
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            value = [item.strip() for item in text.split(",") if item.strip()]

    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray, str)):
        raise ValueError("Daftar label harus berupa array JSON.")

    parsed: List[Dict[str, Any]] = []
    for item in value:
        if isinstance(item, str):
            key = _slug(item)
            parsed.append({
                "key": key,
                "name": key.replace("_", " ").title(),
                "description": f"Kategori {key.replace('_', ' ')}.",
                "examples": [],
            })
            continue
        if not isinstance(item, dict):
            raise ValueError("Setiap label harus berupa objek.")
        key = _slug(item.get("key"))
        name = str(item.get("name") or "").strip()
        description = str(item.get("description") or "").strip()
        examples = item.get("examples") or []
        if not isinstance(examples, list):
            raise ValueError(f"Examples untuk label {key or name!r} harus berupa array.")
        parsed.append({
            "key": key,
            "name": name,
            "description": description,
            "examples": [str(example).strip() for example in examples if str(example).strip()][:3],
        })
    return parsed


def validate_axis(value: Any, axis: str) -> List[Dict[str, Any]]:
    if axis not in AXIS_RULES:
        raise ValueError(f"Axis taxonomy tidak dikenal: {axis}")
    labels = parse_labels(value)
    rules = AXIS_RULES[axis]
    if not rules["minimum"] <= len(labels) <= rules["maximum"]:
        raise ValueError(
            f"{axis} harus memiliki {rules['minimum']}-{rules['maximum']} label."
        )

    keys, names = set(), set()
    for label in labels:
        key = label["key"]
        name_key = label["name"].casefold()
        if not key or not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", key):
            raise ValueError(f"Key label tidak valid: {key!r}")
        if not label["name"] or not label["description"]:
            raise ValueError(f"Label {key!r} wajib memiliki nama dan deskripsi.")
        if key in keys or name_key in names:
            raise ValueError(f"Label duplikat pada {axis}: {key}")
        keys.add(key)
        names.add(name_key)

    required = rules["required"]
    if required not in keys:
        raise ValueError(f"{axis} wajib memiliki label {required!r}.")
    return labels


def validate_config(prompt_context: Any, issues: Any, stances: Any, actions: Any) -> Dict[str, Any]:
    prompt = str(prompt_context or "").strip()
    if not prompt:
        raise ValueError("Prompt context tidak boleh kosong.")
    return {
        "prompt_context": prompt,
        "issues": validate_axis(issues, "issues"),
        "stances": validate_axis(stances, "stances"),
        "actions": validate_axis(actions, "actions"),
    }


def dumps_labels(labels: Any) -> str:
    return json.dumps(parse_labels(labels), ensure_ascii=False, separators=(",", ":"))


def label_keys(value: Any) -> List[str]:
    return [label["key"] for label in parse_labels(value)]
