from .csv import CSVExporter


class AnkiExporter(CSVExporter):
    def __init__(self) -> None:
        super().__init__(
            delimiter="\t",
            columns=[
                "canonical_form",
                "translations",
                "part_of_speech",
                "gender",
                "irregular",
                "example_sentence",
                "example_translation",
                "disambiguation_note",
            ],
            column_mapping={
                "canonical_form": "Word",
                "translations": "Translation",
                "part_of_speech": "Part of Speech",
                "gender": "Gender",
                "example_sentence": "Example Sentence",
                "example_translation": "Example Translation",
                "disambiguation_note": "Disambiguation",
            },
            list_separator=", ",
        )
