# Zotero source lookup

For Zotero tasks use the installed `zotero:Zotero` skill, resolving its current plugin path. Recheck availability with `status --json`; do not reuse old item/collection keys, attachment paths or service status as current facts.

Search and match title, authors/year, collection, parent item and PDF attachment keys. Use `children` / `file-url` read-only helpers to locate the PDF; record source path, page count and SHA-256. A unique identified target needs no repeated confirmation; ask only if ambiguous. Put generated work outside source storage; keep original PDF and bibliographic metadata, with no duplicate paper item.

Only when saving is requested, also read [save verification](zotero-save.md). Translation or skill testing alone does not authorize a save.
