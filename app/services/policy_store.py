import json
from pathlib import Path

from app.models.policy import PolicyVersion

DEFAULT_STORAGE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "policy_versions.json"


def _load(storage_path: Path) -> list[dict]:
    if not storage_path.exists():
        return []
    with open(storage_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _dump(storage_path: Path, records: list[dict]) -> None:
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    with open(storage_path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=2)


def save_policy_version(version: PolicyVersion, storage_path: Path | None = None) -> None:
    path = storage_path or DEFAULT_STORAGE_PATH
    records = _load(path)
    records = [record for record in records if record.get("version_id") != version.version_id]
    records.append(version.model_dump(mode="json"))
    _dump(path, records)


def list_policy_versions(storage_path: Path | None = None) -> list[PolicyVersion]:
    path = storage_path or DEFAULT_STORAGE_PATH
    return [PolicyVersion.model_validate(record) for record in _load(path)]