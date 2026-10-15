# Conditional setup and special inputs

Read only the relevant section; return to the normal workflow afterward.

## Environment / fonts
If the prepared interpreter is absent, check Codex bundled runtime first. If necessary create only a skill-specific environment, not system Python:
```sh
uv venv ~/.cache/codex-trans/venv --python python3
uv pip install --python ~/.cache/codex-trans/venv/bin/python 'PyMuPDF>=1.26.5'
```
Verify Python 3.10+ and the dependency before using it. Custom font: `build --font /path/font.ttf` or top-level manifest `font`; TTF/OTF only, relative paths resolve against the manifest directory. Check Chinese, Latin and math glyphs for missing characters and searchable extraction. Default CJK font is bundled, without network downloads.

## Special layouts
Scans require a verified OCR text layer, then fresh source hash and coordinates. Colored backgrounds or text over images need separate adaptation; never paint white boxes blindly. Annotations/form appearances are baked on the in-memory copy; source bytes stay intact. Links/interactivity are NOT guaranteed in the output.
Complex inline math requires refined original-coordinate regions or separately verified exact formula typesetting. Preserve meaning and symbols; never flatten complex expressions to ambiguous plain text. Unresolved fit/geometry remains a blocking issue under the entrypoint's overflow rule.

## Explicit image-generation request only
Use an installed image-generation tool/skill only when explicitly requested. Explain that bitmap Chinese pages alone are not searchable; if searchability is still required, add AND verify an OCR layer. On service failure report it and retain progress; never automatically switch to paid APIs. Resolve unknown request status before resubmission.
