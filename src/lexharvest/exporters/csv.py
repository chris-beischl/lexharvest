import csv
from pathlib import Path

from lexharvest.db.models import VocabEntry

from .base import BaseExporter


class CSVExporter(BaseExporter):
    def __init__(
        self,
        delimiter: str = ",",
        columns: list[str] | None = None,
        column_mapping: dict[str, str] | None = None,
        list_separator: str = "; ",
    ):
        self.delimiter = delimiter
        self.columns = set(columns) if columns is not None else None
        self.column_mapping = column_mapping or {}
        self.list_separator = list_separator

    def export(self, entries: list[VocabEntry], output_path: Path) -> None:
        entry_dicts = [e.model_dump(include=self.columns) for e in entries]
        mapped_dicts = []
        for d in entry_dicts:
            mapped_dict = {
                self.column_mapping.get(k, k): self.list_separator.join(v)
                if isinstance(v, list)
                else v
                for k, v in d.items()
            }
            mapped_dicts.append(mapped_dict)

        if not mapped_dicts:
            return  # No entries to write

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = mapped_dicts[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=self.delimiter)
            writer.writeheader()
            writer.writerows(mapped_dicts)
