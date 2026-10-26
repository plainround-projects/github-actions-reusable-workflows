"""``python -m search DOCUMENTS.jsonl QUERY...`` prints the matching document ids with their scores."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from search.application.search_documents import SearchDocuments
from search.infrastructure.jsonl_source import JsonLinesDocuments


def main(argv: Sequence[str] | None = None) -> int:
    """Run the program; return 0 on success, 1 for an unreadable file and 2 for a usage error."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        print("usage: python -m search DOCUMENTS.jsonl QUERY...", file=sys.stderr)
        return 2
    try:
        results = SearchDocuments(JsonLinesDocuments(Path(args[0])))(" ".join(args[1:]))
    except (OSError, ValueError) as error:
        print(f"search: {error}", file=sys.stderr)
        return 1
    for doc_id, score in results:
        print(f"{doc_id}\t{score}")
    return 0
