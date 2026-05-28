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
                "article",
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
                "article": "Article",
                "example_sentence": "Example Sentence",
                "example_translation": "Example Translation",
                "disambiguation_note": "Disambiguation",
            },
            value_mapping={
                "Gender": {
                    "masculine": "m",
                    "feminine": "f",
                    "neuter": "n",
                },
                "irregular": {
                    True: "irregular",
                    False: None,
                },
            },
            list_separator=", ",
        )
