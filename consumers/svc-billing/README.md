# svc-billing

A small service (domain, application, infrastructure, interfaces) that issues invoices with tax: exact `Decimal`
arithmetic, tax rounded half-even to the cent once on the subtotal. Its whole CI is
[`.github/workflows/ci.yml`](.github/workflows/ci.yml), under fifteen lines, and it passes **one named secret**,
`PACKAGE_TOKEN`, to the shared workflow: the shared workflow can read that secret and nothing else.

In the lesson this folder is its own repository, `svc-billing`.

```bash
python -m pip install --require-hashes -r requirements.txt
python -m pytest -q
PYTHONPATH=src python -m billing i-1 0.0825 widget:3:19.99   # i-1: subtotal 59.97 tax 4.95 total 64.92
```
