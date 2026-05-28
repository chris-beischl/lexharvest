from pathlib import Path
from typing import Protocol

from lexharvest.db.models import VocabEntry


class BaseExporter(Protocol):
    def export(self, entries: list[VocabEntry], output_path: Path) -> None: ...
