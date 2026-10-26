"""Documents from a JSON Lines file: one ``{"id": ..., "text": ...}`` object per line."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from search.domain.index import Document


class JsonLinesDocuments:
    """:class:`~search.application.search_documents.DocumentSource` backed by a file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def documents(self) -> Iterator[Document]:
        """Yield the documents of the file; a blank line is skipped, a malformed line raises ``ValueError``."""
        for number, line in enumerate(self._path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                yield Document(str(record["id"]), str(record["text"]))
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                raise ValueError(f"{self._path}:{number}: not a document: {error}") from error
