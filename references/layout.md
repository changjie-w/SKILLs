# Layout contract

Use Python 3.10+ with PyMuPDF 1.26.5+; try `~/.cache/codex-trans/venv/bin/python`. If unavailable, read [environment](exceptions.md). Below `python` is that verified interpreter and `<skill>` is this skill folder. Put all work outside the skill folder.

```sh
python <skill>/scripts/pdf_regions.py inspect --source paper.pdf --output inventory.json --render-dir source-previews
python <skill>/scripts/pdf_regions.py view --input inventory.json --kind inventory --pages 1
python <skill>/scripts/pdf_regions.py build --source paper.pdf --plan layout.json --output bilingual.pdf --report file-checks.json --render-dir final-previews
python <skill>/scripts/pdf_regions.py view --input file-checks.json --kind report
```

`inspect --pages 1-3` selects 1-based pages; omission inspects all. Inventory provides lines, images and drawing bounds, NOT semantic regions. Keep complete files on disk; read current pages with `view`, not the entire inventory repeatedly. Inventory `view` without pages gives an index; with pages it includes ALL selected text/geometry. Compact line rows are `[rect,text,direction?,extra_fields?]`, default direction `[1,0]`; non-default directions are explicit. Report view preserves overall facts, page statuses, errors and unassessed review states, omitting region diagnostics. `--detail full` expands unchanged data (optionally selected pages); read details when needed. None of these views truncates text or rounds coordinates.

## Manifest v1

Example SHAPE only: replace hashes/text/coordinates from actual input; never reuse example coordinates.
```json
{"version":1,"source_sha256":"inventory hash","pages":[{"source_page":1,"mode":"translate","translations":[{"id":"body","rect":[40,60,280,180],"text":"完整译文"},{"id":"caption","kind":"caption","for":"figure","rect":[40,400,280,445],"text":"图注译文"}],"preserve":[{"id":"figure","kind":"figure","rect":[40,190,280,390]}]},{"source_page":2,"mode":"copy","reason":"references"}]}
```
- Default covers ALL source pages. Partial requests require top-level `scope:[1,2]`; `pages` must match scope exactly, once each, ascending. Never hide failed pages with scope. Copy mode is ONLY for reference-only pages, not mixed pages.
- Coordinates: points (1/72 inch), displayed page's top-left origin after rotation normalization; use `inspect`. Rectangles remain at original positions, never span columns. Translation rectangles must not overlap each other or protected regions; leave glyph clearance.
- Each translation requires page-unique `id`, `rect`, `text`. `text` is UTF-8 plain text, HTML escaped, newlines retained; list regions in reading order. `kind`: title/heading/body(default)/algorithm/caption. A caption's `for` must name a same-page preserved figure/table; manually document cross-page relationships, never invent a same-page link.
- Optional per-region `font_size` (default 10 pt), `min_font_size` (90% of initial), `line_height` (1.2), `align` (left/default, center, right, justify). Choose readable limits from the original and preview; overflow fails rather than bypassing the minimum. `no_padding:true` removes extra HTML padding for that region (default false); report records its use. Check glyph bounds: insertion fit alone is insufficient. Bundled CJK fallback needs no download; custom fonts: [exceptions](exceptions.md). With ANY font, verify searchable Chinese, Latin and math glyphs without missing characters.
- Preserve records require page-unique `id`, `rect`, and `kind`: authors/publication/references/figure/table/formula/page_number/other. `other` requires `reason`, not a loophole to leave prose untranslated. Every extractable nonspace source character must be classified (tested by its center); coverage does not prove correct classification or faithful translation. Unspecified background is still reused.
- Inline formulas: protect original formula areas and split surrounding prose; for complex cases read [exceptions](exceptions.md). Do not replace ambiguous formulas with guessed plain text.

## Build and verification

The helper does NOT translate, call APIs or operate Zotero. It copies the page, removes text and paints white only in translation rectangles, adds searchable Chinese, and embeds original/translated pages at original scale. Figures/vectors remain in place. Default input: white-background papers with a text layer. For scans, colored/image-backed text or annotations read [exceptions](exceptions.md) BEFORE processing.

Output/report paths must be unused; use new names for revisions. Staging is reopened and checked before publishing: page count/scope and double-width dimensions; unchanged source SHA-256; original left and protected right pixels at 72 dpi; per-region extracted text equals input after Unicode NFKC/whitespace normalization; glyph bounds; caption mapping and region/font/scale diagnostics. Errors identify page/region and block publication; inspect the error report. These checks do not prove semantic correctness or reading order.

`--render-dir` produces 120 dpi previews. Inspect every page, including classification and column order; check formula subscripts/superscripts, brackets, matrices, minus signs, summation bounds and numbers. Keep the separate visual/accuracy records required by the entrypoint; complete accuracy review before saving to Zotero.
