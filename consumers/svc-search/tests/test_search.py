import pytest

from search.application.search_documents import SearchDocuments
from search.domain.index import Document, InvertedIndex, tokenize
from search.infrastructure.jsonl_source import JsonLinesDocuments
from search.interfaces.cli import main

DOCS = [
    Document("a", "Caching makes the build fast"),
    Document("b", "A cache key is a hash of the lock file"),
    Document("c", "Fast builds and fast tests"),
]


class ListSource:
    def documents(self):
        return DOCS


def test_tokenizing_lowercases_and_drops_stop_words():
    assert tokenize("The Cache, and a KEY!") == ["cache", "key"]


def test_a_query_matches_documents_that_contain_every_term():
    index = InvertedIndex()
    for document in DOCS:
        index.add(document)
    assert index.search("fast build") == [("a", 2)]
    assert index.search("fast cache") == []
    assert index.search("fast") == [("c", 2), ("a", 1)]


def test_a_query_of_only_stop_words_matches_nothing():
    assert InvertedIndex().search("the and") == []


def test_the_use_case_indexes_a_source_once_and_answers_queries():
    search = SearchDocuments(ListSource())
    assert search("cache key") == [("b", 2)]
    assert search("missing") == []


def test_the_file_source_reads_json_lines_and_skips_blank_lines(tmp_path):
    path = tmp_path / "docs.jsonl"
    path.write_text('{"id": "x", "text": "hello world"}\n\n{"id": "y", "text": "world"}\n', encoding="utf-8")
    assert [d.doc_id for d in JsonLinesDocuments(path).documents()] == ["x", "y"]


def test_a_malformed_line_names_the_file_and_the_line(tmp_path):
    path = tmp_path / "docs.jsonl"
    path.write_text('{"id": "x"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"docs.jsonl:1"):
        list(JsonLinesDocuments(path).documents())


def test_the_command_prints_ids_and_scores(tmp_path, capsys):
    path = tmp_path / "docs.jsonl"
    path.write_text('{"id": "x", "text": "hello hello world"}\n{"id": "y", "text": "hello"}\n', encoding="utf-8")
    assert main([str(path), "hello"]) == 0
    assert capsys.readouterr().out.splitlines() == ["x\t2", "y\t1"]


def test_the_command_reports_a_missing_file_with_exit_code_1(tmp_path, capsys):
    assert main([str(tmp_path / "none.jsonl"), "x"]) == 1
    assert "search:" in capsys.readouterr().err


def test_the_command_without_arguments_is_a_usage_error(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err
