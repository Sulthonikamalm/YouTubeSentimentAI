import pytest

from backend.services.taxonomy_config import parse_labels, validate_config


def _labels(prefix, count, required):
    labels = [
        {"key": f"{prefix}_{index}", "name": f"{prefix} {index}", "description": f"Deskripsi {index}", "examples": []}
        for index in range(count)
    ]
    labels[-1] = {"key": required, "name": required, "description": "Fallback", "examples": []}
    return labels


def test_validate_structured_taxonomy():
    result = validate_config(
        "Konteks project",
        _labels("issue", 5, "lainnya"),
        _labels("stance", 3, "tidak_terdeteksi"),
        _labels("action", 4, "tidak_terdeteksi"),
    )
    assert result["issues"][-1]["key"] == "lainnya"


def test_duplicate_and_missing_required_labels_are_rejected():
    issues = _labels("issue", 5, "lainnya")
    issues[1]["key"] = issues[0]["key"]
    with pytest.raises(ValueError, match="duplikat"):
        validate_config(
            "Konteks", issues,
            _labels("stance", 3, "tidak_terdeteksi"),
            _labels("action", 4, "tidak_terdeteksi"),
        )


def test_legacy_csv_labels_remain_readable():
    parsed = parse_labels("ekonomi, pendidikan")
    assert [label["key"] for label in parsed] == ["ekonomi", "pendidikan"]
