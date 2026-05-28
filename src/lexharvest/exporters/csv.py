import csv
from pathlib import Path
from typing import Any

from lexharvest.db.models import VocabEntry

from .base import BaseExporter, get_mapped_dicts


class CSVExporter(BaseExporter):
    def __init__(
        self,
        delimiter: str = ",",
        columns: list[str] | None = None,
        column_mapping: dict[str, str] | None = None,
        value_mapping: dict[str, dict[Any, Any]] | None = None,
        list_separator: str = "; ",
        **kwargs: Any,
    ):
        self.delimiter = delimiter
        self.columns = columns
        self.column_mapping = column_mapping or {}
        self.value_mapping = value_mapping or {}
        self.list_separator = list_separator

    def export(self, entries: list[VocabEntry], output_path: Path) -> None:
        mapped_dicts = get_mapped_dicts(
            entries,
            columns=self.columns,
            column_mapping=self.column_mapping,
            value_mapping=self.value_mapping,
            list_separator=self.list_separator,
        )

        if not mapped_dicts:
            return  # No entries to write

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = mapped_dicts[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=self.delimiter)
            writer.writeheader()
            writer.writerows(mapped_dicts)
