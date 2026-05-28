from pathlib import Path
from typing import Any

import genanki
import tomllib

from lexharvest.db.models import VocabEntry

from .base import BaseExporter, get_mapped_dicts
from .csv import CSVExporter

_DEFAULT_TEMPLATE_PATH = Path("anki_template.toml")


def _load_anki_template(template_path: Path = _DEFAULT_TEMPLATE_PATH) -> dict[str, Any]:
    with open(template_path, "rb") as f:
        template = tomllib.load(f)
    template["value_mapping"] = template.get("value_mapping", {})
    return template


class AnkiExporter(CSVExporter):
    def __init__(self, template_path: Path = _DEFAULT_TEMPLATE_PATH, **kwargs: Any) -> None:
        template = _load_anki_template(template_path)

        super().__init__(
            delimiter="\t",
            columns=template["columns"],
            column_mapping=template["columns_to_fields_mapping"],
            value_mapping=template["value_mapping"],
            list_separator=template["list_separator"],
        )


class AnkiPackageExporter(BaseExporter):
    def __init__(
        self,
        model_id: int | None = None,
        model_name: str | None = None,
        deck_id: int | None = None,
        deck_name: str | None = None,
        template_path: Path = _DEFAULT_TEMPLATE_PATH,
        **kwargs: Any,
    ) -> None:
        with open(template_path, "rb") as f:
            template = tomllib.load(f)

        model_id = model_id or template.get("model_id")
        if model_id is None:
            raise ValueError(
                "model_id must be provided either as an argument or in \
                the template"
            )
        model_name = model_name or template.get("model_name")
        if model_name is None:
            raise ValueError(
                "model_name must be provided either as an argument or in \
                the template"
            )
        deck_id = deck_id or template.get("deck_id")
        if deck_id is None:
            raise ValueError(
                "deck_id must be provided either as an argument or in \
                the template"
            )
        deck_name = deck_name or template.get("deck_name")
        if deck_name is None:
            raise ValueError(
                "deck_name must be provided either as an argument or in \
                the template"
            )

        self.template = template

        fields = [{"name": field_name} for field_name in template["fields"]]
        templates = [
            {
                "name": "source->target",
                "qfmt": template["source_to_target"]["front"],
                "afmt": template["source_to_target"]["back"],
            },
            {
                "name": "target->source",
                "qfmt": template["target_to_source"]["front"],
                "afmt": template["target_to_source"]["back"],
            },
        ]

        self.model = genanki.Model(
            model_id,
            model_name,
            fields=fields,
            templates=templates,
            css=template.get("css", ""),
        )

        self.deck = genanki.Deck(deck_id, template.get("deck_name", deck_name))

    def export(self, entries: list[VocabEntry], output_path: Path) -> None:
        mapped_dicts = get_mapped_dicts(
            entries,
            columns=self.template["columns"],
            column_mapping=self.template["columns_to_fields_mapping"],
            value_mapping=self.template.get("value_mapping", {}),
            list_separator=self.template.get("list_separator", ", "),
        )

        for entry_dict in mapped_dicts:
            fields = [entry_dict.get(field["name"], "") for field in self.model.fields]
            fields = [str(field) if field is not None else "" for field in fields]

            note = genanki.Note(
                model=self.model,
                fields=fields,
                guid=entry_dict.get(
                    "ID"
                ),  # Optional: use entry ID as GUID for better sync behavior
            )
            self.deck.add_note(note)

        package = genanki.Package(self.deck)
        package.write_to_file(output_path)
