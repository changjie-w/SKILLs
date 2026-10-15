# Save a verified derivative

An explicit request to translate and save back authorizes adding the derivative to that original item; do not ask for the same authorization again. Translation/skill creation/testing alone does not. Tests must never create attachments.

1. Complete file, every-page visual and translation-accuracy reviews. Record parent key, final PDF absolute path, SHA-256 and title, e.g. `全文英中对照（左英右中）`; include requested source page numbers in partial-scope titles.
2. Read current children. Same parent + same file hash: do not add a duplicate. Same title alone is insufficient. Never overwrite/delete older derivatives.
3. Use an available official client/supported interface that explicitly creates a STORED attachment under an existing parent. In the UI select that exact parent and attach a stored file copy, not a linked file. Do not import BibTeX/RIS, invent local write endpoints, edit SQLite or place files manually in storage.
4. Read back: attachment title, `parentItem`, PDF MIME, stored-import `linkMode` (usually `imported_file`, underlying 0; verify against current interface), accessible storage path, openable PDF and expected page count, stored file SHA-256 equal to delivered PDF. Confirm original attachment still exists unchanged and parent metadata is unchanged.
5. Record actual values/pass/fail in `zotero-save-verification.json`. Timeout, unclear UI result or uncertain parent: read children and compare hashes before any retry. Do not retry while the outcome remains unknown. After ONE definite failure with its cause fixed, retry at most once; if still failing deliver the local PDF and report save incomplete.

If parent/storage type/hash cannot be read back, never claim a verified save; deliver the usable PDF and identify outstanding verification.
