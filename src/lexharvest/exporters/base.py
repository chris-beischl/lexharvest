from pathlib import Path
from typing import Any, Protocol

from lexharvest.db.models import VocabEntry


class BaseExporter(Protocol):
    def export(self, entries: list[VocabEntry], output_path: Path) -> None: ...


def _map_value(column: Any, value: Any, mapping: dict[Any, Any]) -> Any:
    if column in mapping:
        if isinstance(value, bool):
            value = str(value).lower()  # Convert bool to "true"/"false" for mapping
        return mapping[column].get(value, value)
    return value


def get_mapped_dicts(
    entries: list[VocabEntry],
    columns: list[str] | None = None,
    column_mapping: dict[str, str] | None = None,
    value_mapping: dict[str, dict[Any, Any]] | None = None,
    list_separator: str = "; ",
) -> list[dict[str, Any]]:
    cols = set(columns) if columns is not None else None
    column_mapping = column_mapping or {}
    value_mapping = value_mapping or {}

    entry_dicts = [e.model_dump(include=cols) for e in entries]
    mapped_dicts = []
    for d in entry_dicts:
        column_mapped_dict = {
            column_mapping.get(k, k): list_separator.join(v) if isinstance(v, list) else v
            for k, v in d.items()
        }

        value_mapped_dict = {
            column: _map_value(column, value, value_mapping)
            for column, value in column_mapped_dict.items()
        }

        mapped_dicts.append(value_mapped_dict)

    return mapped_dicts
