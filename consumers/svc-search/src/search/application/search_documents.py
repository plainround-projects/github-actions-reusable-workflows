"""Use cases: build an index from a document source and answer queries."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from search.domain.index import Document, InvertedIndex


class DocumentSource(Protocol):
    """Where documents come from."""

    def documents(self) -> Iterable[Document]:
        """Yield every document once."""
        ...


class SearchDocuments:
    """Index a source once, then answer any number of queries."""

    def __init__(self, source: DocumentSource) -> None:
        self._index = InvertedIndex()
        for document in source.documents():
            self._index.add(document)

    def __call__(self, query: str) -> list[tuple[str, int]]:
        """Return ``(doc_id, score)`` for the documents matching ``query``."""
        return self._index.search(query)
