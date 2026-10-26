# svc-orders

A small service (domain, application, infrastructure, interfaces) that places orders and prices them in whole cents.
It exists to be built and tested by the shared `build-test` workflow of the platform repository: its whole CI is
[`.github/workflows/ci.yml`](.github/workflows/ci.yml), under fifteen lines.

In the lesson this folder is its own repository, `svc-orders`. Secrets passed to the shared workflow: **none**
(the default; the shared workflow can read nothing).

```bash
python -m pip install --require-hashes -r requirements.txt
python -m pytest -q
PYTHONPATH=src python -m orders o-1 pen:2:150 pad:1:50   # o-1: 3.50
```
