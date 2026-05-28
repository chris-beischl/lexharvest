from .anki import AnkiExporter as AnkiExporter
from .anki import AnkiPackageExporter as AnkiPackageExporter
from .csv import CSVExporter as CSVExporter

EXPORTER_REGISTRY = {
    "csv": CSVExporter,
    "anki-tsv": AnkiExporter,
    "anki-apkg": AnkiPackageExporter,
}
