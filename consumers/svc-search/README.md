# svc-search

A small service (domain, application, infrastructure, interfaces): a tokenizer and an inverted index over JSON Lines
documents. Its whole CI is [`.github/workflows/ci.yml`](.github/workflows/ci.yml), under fifteen lines. It calls the
shared workflow pinned to a **full commit SHA**, and it uses `secrets: inherit`, the form the platform's policy does
not allow (see the secrets table in the platform README); it stays here as the example of what `inherit` hands over.

In the lesson this folder is its own repository, `svc-search`.

```bash
python -m pip install --require-hashes -r requirements.txt
python -m pytest -q
PYTHONPATH=src python -m search docs.jsonl cache key
```
