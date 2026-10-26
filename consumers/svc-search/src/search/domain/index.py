"""Words become terms; an inverted index maps each term to the documents that contain it."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

STOP_WORDS = frozenset({"a", "an", "and", "the", "of", "to", "in", "is"})
_WORD = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase ``text`` and return its words, without stop words, in order."""
    return [word for word in _WORD.findall(text.lower()) if word not in STOP_WORDS]


@dataclass(frozen=True, slots=True)
class Document:
    """A document id and its text."""

    doc_id: str
    text: str


class InvertedIndex:
    """Maps terms to ``{doc_id: occurrences}``; a query matches documents that contain every query term."""

    def __init__(self) -> None:
        self._postings: dict[str, Counter[str]] = {}

    def add(self, document: Document) -> None:
        """Index ``document``; adding the same id again counts its words twice, so callers add each id once."""
        for term in tokenize(document.text):
            self._postings.setdefault(term, Counter())[document.doc_id] += 1

    def search(self, query: str) -> list[tuple[str, int]]:
        """Return ``(doc_id, score)`` for documents containing every term, best score first, ties by id."""
        terms = tokenize(query)
        if not terms:
            return []
        matching: set[str] | None = None
        for term in terms:
            ids = set(self._postings.get(term, {}))
            matching = ids if matching is None else matching & ids
        scores = {doc: sum(self._postings[term][doc] for term in terms) for doc in matching or set()}
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))
