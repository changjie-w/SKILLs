# Helper maintenance

Run `python <skill>/scripts/test_pdf_regions.py` for isolated synthetic regression tests (no Zotero/network). They cover sizes, mixed/pure references, formulas, caption links, rotation, overflow and compact views. Use only authorized real files for further regression; record original page/crop provenance. Excerpt success does not prove full-paper translation accuracy.

Use normal commands without loading Python source. Inspect relevant implementation only for a demonstrated failure or maintenance request. API reference when needed: https://pymupdf.readthedocs.io/en/latest/page.html .
