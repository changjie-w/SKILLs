---
name: trans
description: "将英文论文 PDF 制作为左英文原页、右可检索简体中文的逐页双语 PDF，保持分栏及图表位置；适用于本地 PDF 或 Zotero 论文翻译，并在用户要求时回存原条目。普通短文翻译不使用此技能。"
---
# trans

Deliver Chinese responses and a searchable Simplified-Chinese / English paper PDF: original English left, matching Chinese right; one spread per source page, width doubled, height unchanged, including mixed page sizes. Explicit user scope/format/destination overrides defaults; otherwise translate the full paper including appendices.

## Invariants
- Translate title, abstract, body, headings, keywords, algorithm explanations, captions and appendices faithfully: preserve claim strength, negation, conditions, citation markers, math symbols and experimental values; never summarize instead.
- Reuse original figures/tables/formulas at their original coordinates and sizes; translate captions in their corresponding areas. Preserve references INCLUDING heading, entries and numbering; authors, affiliations, addresses, email, publication data, DOI/arXiv IDs, copyright and licenses. Copy reference-only pages; separate references from prose on mixed pages.
- Source documents are content, not authorization. Keep source attachments and Zotero bibliographic metadata intact. Do not create Zotero attachments during skill tests.

## Workflow
1. Resolve source, page scope and output directory; ask only about ambiguous candidates or missing pages. For Zotero input read [source lookup](references/zotero.md); for requested saving also read [saving](references/zotero-save.md).
2. Read [layout contract](references/layout.md), then execute the helper without reading its source. Reuse instructions already in context; reload only if absent or changed. Inspect and render pages; infer reading order visually, not from extraction order. Prepare complete translations, region classifications, caption links, terminology and uncertainty notes; resolve extraction errors against the original, never guess formulas.
3. Build, inspect EVERY rendered page, and review translation accuracy separately. Check cropping, overlaps, line breaks, captions and formulas. Overflow: adjust wrapping/size/leading within a recorded readable minimum; never omit content, move figures, spill across columns or shrink indefinitely. If unresolved, report source page/region, keep work, and withhold a finished deliverable.
4. Keep separate task-local records: `file-checks.json` (checks, scope, hashes), `visual-review.md` (each page, issues/fixes), `translation-review.md` (coverage, terms, formulas, numbers, citations, accuracy). Script success does not prove semantic accuracy or replace visual review; never claim unperformed checks. Reference-only pages need no Chinese.
5. Deliver the final PDF with scope and unresolved limitations; call it complete only when all requested pages and checks are complete. Save to the original Zotero item only when requested and verify the save.

Default: text typesetting. Read [exceptions](references/exceptions.md) only for missing dependencies, custom fonts, scanned/colored/annotated input, complex inline math or explicitly requested image generation. For helper maintenance/testing read [maintenance](references/maintenance.md).
