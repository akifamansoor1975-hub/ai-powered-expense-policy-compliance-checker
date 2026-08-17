import json
from pathlib import Path

from app.models.compliance import ComplianceResult

DEFAULT_STORAGE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "compliance_results.json"


def _load(storage_path: Path) -> dict:
    if not storage_path.exists():
        return {}
    with open(storage_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _dump(storage_path: Path, records: dict) -> None:
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    with open(storage_path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=2)


def save_compliance_result(result_id: str, result: ComplianceResult, storage_path: Path | None = None) -> None:
    path = storage_path or DEFAULT_STORAGE_PATH
    records = _load(path)
    records[result_id] = result.model_dump(mode="json")
    _dump(path, records)


def get_compliance_result(result_id: str, storage_path: Path | None = None) -> ComplianceResult | None:
    path = storage_path or DEFAULT_STORAGE_PATH
    record = _load(path).get(result_id)
    if record is None:
        return None
    return ComplianceResult.model_validate(record)