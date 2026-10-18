#!/usr/bin/env python3
"""Inspect PDFs and compose searchable region-based bilingual pages. No network I/O."""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import unicodedata

import pymupdf as fitz


class LayoutError(ValueError):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized(text):
    return "".join(unicodedata.normalize("NFKC", text).split())


def require(condition, message):
    if not condition:
        raise LayoutError(message)


def rect(value, page, label):
    require(isinstance(value, list) and len(value) == 4
            and all(isinstance(v, (int, float)) and math.isfinite(v) for v in value),
            f"{label}: rect must contain four finite coordinates")
    box = fitz.Rect(value)
    require(not box.is_empty and page.rect.contains(box), f"{label}: rect outside page or empty: {value}")
    return box


def source_doc(path):
    document = fitz.open(path)
    require(document.is_pdf and not document.needs_pass, "Source must be an unlocked PDF")
    # Work only in memory. Bake visible annotations so show_pdf_page retains them.
    document.bake(annots=True, widgets=True)
    for page in document:
        if page.rotation:
            page.remove_rotation()
    return document


def characters(page):
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                yield from span["chars"]


def select_pages(spec, count):
    if not spec:
        return list(range(1, count + 1))
    selected = []
    for part in spec.split(","):
        match = re.fullmatch(r"(\d+)(?:-(\d+))?", part.strip())
        require(match is not None, f"Invalid page selection: {part}")
        first, last = int(match[1]), int(match[2] or match[1])
        require(1 <= first <= last <= count, f"Page range outside source: {part}")
        selected.extend(range(first, last + 1))
    require(selected == sorted(set(selected)), "Pages must be unique and ascending")
    return selected


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def render_page(page, directory, number):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"page-{number:04d}.png"
    require(not target.exists(), f"Preview already exists: {target}")
    page.get_pixmap(dpi=120, annots=False).save(target)


def inspect_pdf(source, output, pages=None, render_dir=None):
    require(not Path(output).exists(), f"Inventory already exists: {output}")
    doc = source_doc(source)
    inventory = {"version": 1, "source": str(Path(source).resolve()),
                 "source_sha256": digest(source), "page_count": len(doc), "pages": []}
    for number in select_pages(pages, len(doc)):
        page = doc[number - 1]
        lines = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                lines.append({"rect": list(line["bbox"]), "direction": list(line["dir"]),
                              "text": "".join(span["text"] for span in line["spans"])})
        inventory["pages"].append({"source_page": number, "size": [page.rect.width, page.rect.height],
                                   "lines": lines,
                                   "images": [list(i["bbox"]) for i in page.get_image_info()],
                                   "drawings": [list(i["rect"]) for i in page.get_drawings()]})
        if render_dir:
            render_page(page, render_dir, number)
    doc.close()
    write_json(output, inventory)
    return inventory


def validate_page(page, item):
    number = item["source_page"]
    label = f"source page {number}"
    if item.get("mode") == "copy":
        require(item.get("reason") == "references", f"{label}: whole-page copy needs reason=references")
        require(not item.get("translations"), f"{label}: copy page cannot contain translations")
        return [], []
    require(item.get("mode") == "translate", f"{label}: mode must be translate or copy")
    translations, protected = item.get("translations", []), item.get("preserve", [])
    require(translations, f"{label}: no translations provided")
    ids, text_boxes, preserve_boxes = set(), [], []
    for region, boxes in [(r, text_boxes) for r in translations] + [(r, preserve_boxes) for r in protected]:
        key = region.get("id")
        require(isinstance(key, str) and key and key not in ids, f"{label}: missing or duplicate region id {key}")
        ids.add(key)
        boxes.append(rect(region.get("rect"), page, f"{label}, region {key}"))
    valid_preserve = {"authors", "publication", "references", "figure", "table", "formula", "page_number", "other"}
    for region in protected:
        require(region.get("kind") in valid_preserve, f"{label}, {region['id']}: invalid preservation kind")
        require(region["kind"] != "other" or region.get("reason"), f"{label}, {region['id']}: other needs reason")
    objects = {r["id"] for r in protected if r["kind"] in {"figure", "table"}}
    for index, region in enumerate(translations):
        key = region["id"]
        require(isinstance(region.get("text"), str) and region["text"].strip(), f"{label}, {key}: text is empty")
        kind = region.get("kind", "body")
        require(kind in {"title", "heading", "body", "algorithm", "caption"}, f"{label}, {key}: invalid kind")
        if kind == "caption":
            require(region.get("for") in objects, f"{label}, {key}: caption has no matching figure/table")
        for other in text_boxes[index + 1:] + preserve_boxes:
            require(not text_boxes[index].intersects(other), f"{label}, {key}: overlaps another region")
    source_chars = [c for c in characters(page) if c["c"].strip()]
    require(source_chars, f"{label}: no source text layer; verify OCR before translation")
    for char in source_chars:
        box = fitz.Rect(char["bbox"])
        center = (box.tl + box.br) / 2
        require(any(b.contains(center) for b in text_boxes + preserve_boxes),
                f"{label}: unclassified source character {char['c']!r} at {list(box)}")
    return text_boxes, preserve_boxes


def put_translation(page, region, font):
    size = float(region.get("font_size", 10))
    minimum = float(region.get("min_font_size", size * 0.9))
    leading = float(region.get("line_height", 1.2))
    require(all(math.isfinite(v) for v in (size, minimum, leading)) and 0 < minimum <= size and leading >= 1,
            f"region {region['id']}: invalid font size, minimum, or line height")
    align = region.get("align", "left")
    require(align in {"left", "center", "right", "justify"}, f"region {region['id']}: invalid alignment")
    no_padding = region.get("no_padding", False)
    require(type(no_padding) is bool, f"region {region['id']}: no_padding must be boolean")
    padding = "0" if no_padding else "0.15em 0 0.1em"
    css = (f"* {{margin:0; padding:0;}} body {{font-family:sans-serif; font-size:{size}pt;"
           f"padding:{padding}; line-height:{leading}; text-align:{align}; color:#000;}}")
    archive = None
    if font:
        require(font.suffix.lower() in {".ttf", ".otf"} and font.is_file(), f"Invalid TTF/OTF font: {font}")
        # A controlled archive alias avoids CSS escaping problems in filesystem names.
        archive = fitz.Archive()
        archive.add((font.read_bytes(), "trans-font" + font.suffix.lower()))
        css += (f"@font-face {{font-family:trans; src:url(trans-font{font.suffix.lower()});}}"
                "body {font-family:trans;}")
    content = '<div lang="zh-Hans">' + html.escape(region["text"]).replace("\n", "<br>") + "</div>"
    spare, scale = page.insert_htmlbox(fitz.Rect(region["rect"]), content, css=css,
                                       archive=archive, scale_low=minimum / size)
    require(spare >= 0, f"region {region['id']}: overflow in {region['rect']} at minimum {minimum:g} pt")
    return {**({"no_padding": True} if no_padding else {}),
            "id": region["id"], "rect": region["rect"], "kind": region.get("kind", "body"),
            "for": region.get("for"), "font_size": size * scale, "scale": scale,
            "spare_height": spare, "input_text_sha256": hashlib.sha256(region["text"].encode()).hexdigest()}


def pixels(page, box, x_shift=0):
    target = fitz.Rect(box) + (x_shift, 0, x_shift, 0)
    pix = page.get_pixmap(matrix=fitz.Matrix(1, 0, 0, 1, -x_shift, 0), clip=target,
                          colorspace=fitz.csRGB, alpha=False, annots=False)
    return pix.width, pix.height, pix.samples


def vector_roundoff_only(reference, result, target):
    """Conservative evidence for sub-pixel drift, not a perceptual similarity test."""
    def paths(page):
        # Text, images and shading need their existing strict checks / visual review.
        if any(kind not in {"fill-path", "stroke-path"} and fitz.Rect(bounds).intersects(target)
               for kind, bounds in page.get_bboxlog()):
            return None
        selected, clips = [], []
        for drawing in page.get_drawings(extended=True):
            level = drawing.get("level", 0)
            clips = [(depth, safe) for depth, safe in clips if depth < level]
            if drawing["type"] == "clip":
                items = drawing["items"]
                safe = (len(items) == 1 and items[0][0] == "re"
                        and items[0][1].contains(target))
                clips.append((level, safe))
                continue
            if drawing["type"] not in {"s", "f", "fs"}:
                return None  # Transparency groups or unsupported operations.
            # PDF width=0 is a visible device hairline, not an empty path.
            margin = max(1, 10 * (drawing.get("width") or 0)) if drawing["type"] in {"s", "fs"} else 0
            bounds = drawing["rect"] + (-margin, -margin, margin, margin)
            if not bounds.intersects(target):
                continue
            if (not target.contains(bounds) or not all(safe for _, safe in clips)
                    or drawing.get("layer")
                    or any(drawing.get(k) not in (None, 1) for k in ("stroke_opacity", "fill_opacity"))):
                return None
            selected.append({k: v for k, v in drawing.items() if k not in {"seqno", "level", "rect"}})
        return selected or None

    def same_geometry(a, b):
        if type(a) is not type(b):
            return False
        if isinstance(a, (fitz.Point, fitz.Rect, fitz.Quad, tuple, list)):
            return len(a) == len(b) and all(same_geometry(x, y) for x, y in zip(a, b))
        if isinstance(a, float):
            return math.isclose(a, b, rel_tol=0, abs_tol=.001)  # points, ~0.00035 mm
        return a == b

    before, after = paths(reference), paths(result)
    return (before is not None and after is not None and len(before) == len(after)
            and all({k: v for k, v in a.items() if k != "items"}
                    == {k: v for k, v in b.items() if k != "items"}
                    and same_geometry(a["items"], b["items"]) for a, b in zip(before, after)))


def compare_pixels(original, result, box, x_shift, label, reference, warnings):
    actual = pixels(result, box, x_shift)
    expected = pixels(reference, box, x_shift)
    if actual != expected:
        target = fitz.Rect(box) + (x_shift, 0, x_shift, 0)
        # A small pixel delta alone never permits lost strokes, symbols or overlays.
        max_delta = max((abs(a - b) for a, b in zip(actual[2], expected[2])), default=0)
        require(actual[:2] == expected[:2] and max_delta <= 16
                and vector_roundoff_only(reference, result, target),
                f"{label}: preserved pixels differ from matched embedding (72 dpi); inspect region boundaries")
        warnings.append({"kind": "vector_roundoff", "check": label, "max_channel_delta": max_delta,
                         "evidence": "Same opaque vector paths/order/styles; coordinate drift <= 0.001 pt; no text/images/complex clipping"})
        return
    # An exact unmodified control is evidence of embedding/rendering effects;
    # pixel counts or color-distance thresholds alone cannot establish safety.
    if actual != pixels(original, box):
        warnings.append({"kind": "embedding_render_difference", "check": label,
                         "evidence": "Exact 72 dpi match to unmodified source embedded at the same position; no pixel tolerance"})


def verify_output(path, source, entries, report):
    with fitz.open(path) as final:
        require(len(final) == len(entries), "Output page count differs")
        for out_index, item in enumerate(entries):
            original, result = source[item["source_page"] - 1], final[out_index]
            width, height = original.rect.width, original.rect.height
            label = f"source page {item['source_page']}"
            require(abs(result.rect.width - 2 * width) < .01 and abs(result.rect.height - height) < .01,
                    f"{label}: output dimensions differ")
            # Match build_pdf's page size, copy path and embedding positions.
            with fitz.open() as reference, fitz.open() as untouched:
                untouched.insert_pdf(source, from_page=item["source_page"] - 1, to_page=item["source_page"] - 1)
                expected = reference.new_page(width=2 * width, height=height)
                expected.show_pdf_page(original.rect, source, item["source_page"] - 1)
                expected.show_pdf_page(original.rect + (width, 0, width, 0), untouched, 0)
                warnings = report.setdefault("warnings", [])
                compare_pixels(original, result, original.rect, 0, f"{label}, English half", expected, warnings)
                if item["mode"] == "copy":
                    compare_pixels(original, result, original.rect, width, f"{label}, references half", expected, warnings)
                else:
                    for region in item.get("preserve", []):
                        compare_pixels(original, result, region["rect"], width, f"{label}, {region['id']}", expected, warnings)
            if item["mode"] != "copy":
                for region in item["translations"]:
                    box = fitz.Rect(region["rect"]) + (width, 0, width, 0)
                    actual = result.get_text("text", clip=box, sort=True)
                    require(normalized(actual) == normalized(region["text"]),
                            f"{label}, {region['id']}: extracted translation differs from input")
                    for char in characters(result):
                        cb = fitz.Rect(char["bbox"])
                        if char["c"].strip() and box.contains((cb.tl + cb.br) / 2):
                            require((box + (-.5, -.5, .5, .5)).contains(cb),
                                    f"{label}, {region['id']}: glyph extends outside region")
            report["pages"][out_index]["file_checks"] = "passed"


def build_pdf(source, plan, output, report_path, font=None, render_dir=None):
    source, plan, output, report_path = map(lambda p: Path(p).resolve(), (source, plan, output, report_path))
    require(len({source, plan, output, report_path}) == 4, "Source, plan, output, and report paths must differ")
    require(not output.exists() and not report_path.exists(), "Output/report exists; choose new paths")
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"status": "failed", "source": str(source), "output": str(output), "pages": [],
              "translation_accuracy": "not_assessed", "visual_review": "not_assessed"}
    try:
        manifest = json.loads(plan.read_text(encoding="utf-8"))
        require(manifest.get("version") == 1, "Plan version must be 1")
        source_hash = digest(source)
        report["source_sha256"] = source_hash
        require(manifest.get("source_sha256") == source_hash, "Source hash differs from layout plan")
        entries = manifest.get("pages", [])
        require(isinstance(entries, list) and entries, "Plan contains no pages")
        src = source_doc(source)
        scope = manifest.get("scope", list(range(1, len(src) + 1)))
        require(isinstance(scope, list) and scope and all(type(n) is int and 1 <= n <= len(src) for n in scope),
                "Invalid plan scope")
        require(scope == sorted(set(scope)) and [p.get("source_page") for p in entries] == scope,
                "Plan pages must exactly cover scope (default: full source), once each and in order")
        report["scope"] = scope
        font_value = font or manifest.get("font")
        font_path = Path(font_value).expanduser() if font_value else None
        if font_path and not font_path.is_absolute():
            font_path = plan.parent / font_path
        final = fitz.open()
        for item in entries:
            number = item["source_page"]
            original = src[number - 1]
            try:
                boxes, _ = validate_page(original, item)
                right = fitz.open()
                right.insert_pdf(src, from_page=number - 1, to_page=number - 1)
                page = right[0]
                for box in boxes:
                    page.add_redact_annot(box, fill=(1, 1, 1), cross_out=False)
                if boxes:
                    page.apply_redactions(images=0, graphics=0, text=0)
                region_reports = [put_translation(page, r, font_path) for r in item.get("translations", [])]
                spread = final.new_page(width=original.rect.width * 2, height=original.rect.height)
                spread.show_pdf_page(original.rect, src, number - 1)
                spread.show_pdf_page(original.rect + (original.rect.width, 0, original.rect.width, 0), right, 0)
                report["pages"].append({"source_page": number, "mode": item["mode"],
                                        "size": [spread.rect.width, spread.rect.height],
                                        "translations": region_reports, "preserve": item.get("preserve", [])})
                right.close()
            except LayoutError as error:
                raise LayoutError(f"source page {number}: {error}") from error
        final.set_metadata({"title": f"{source.stem} - English / Chinese", "subject": "Side-by-side bilingual paper"})
        final.set_toc([[1, f"Source page {n}", i + 1] for i, n in enumerate(scope)])
        with tempfile.TemporaryDirectory(prefix="trans-build-", dir=output.parent) as temporary:
            staged = Path(temporary) / "staged.pdf"
            final.save(staged, garbage=4, deflate=True)
            final.close()
            verify_output(staged, src, entries, report)
            require(digest(source) == source_hash, "Source changed during build")
            if render_dir:
                with fitz.open(staged) as doc:
                    for i, page in enumerate(doc):
                        render_page(page, render_dir, scope[i])
            # Exclusive output creation prevents silently replacing another result.
            with output.open("xb") as stream:
                stream.write(staged.read_bytes())
        src.close()
        report.update(status="file_checks_passed", output_sha256=digest(output), source_unchanged=True)
    except Exception as error:
        report["error"] = str(error)
        write_json(report_path, report)
        raise
    write_json(report_path, report)
    return report


def view_data(path, kind, pages=None, detail="compact"):
    """Read-only presentation of existing inventories/reports; never re-extract PDF data."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    require(isinstance(data, dict), "Input must be a JSON object")
    require(kind in {"inventory", "report"}, "Invalid view kind")
    require(detail in {"compact", "full"}, "Invalid view detail")
    if kind == "inventory":
        require("page_count" in data and "source_sha256" in data, "Input is not an inventory")
    else:
        require("status" in data, "Input is not a build report")
    entries = data.get("pages", [])
    require(isinstance(entries, list), "Input pages must be a list")
    numbers = [p["source_page"] for p in entries]
    require(len(set(numbers)) == len(numbers), "Input contains duplicate source pages")
    if pages is not None:
        selected = select_pages(pages, max(numbers, default=0))
        require(set(selected) <= set(numbers), "Requested pages are absent from input; inspect them first")
        entries = [p for p in entries if p["source_page"] in selected]
    if detail == "full":
        return {**data, "pages": entries} if pages is not None else data
    if kind == "report":
        # Keep all top-level facts, including global failure and unassessed review states.
        # Omit only successful-region diagnostics; --detail full exposes them unchanged.
        result = {k: v for k, v in data.items() if k != "pages"}
        result["total_pages_recorded"] = len(numbers)
        result["pages"] = [{k: v for k, v in p.items() if k not in {"translations", "preserve"}}
                           for p in entries]
        return result
    result = {k: v for k, v in data.items() if k != "pages"}
    if pages is None:
        result["view"] = "index"
        result["pages"] = [{"source_page": p["source_page"], "size": p["size"],
                            "counts": {k: len(p[k]) for k in ("lines", "images", "drawings")}}
                           for p in entries]
        return result
    result["view"] = "compact-pages"
    result["line_format"] = ["rect", "text", "direction_if_not_default", "extra_fields_if_any"]
    result["default_direction"] = [1.0, 0.0]
    compact = []
    for page in entries:
        lines = []
        for line in page["lines"]:
            row = [line["rect"], line["text"]]
            extra = {k: v for k, v in line.items() if k not in {"rect", "text", "direction"}}
            if line["direction"] != result["default_direction"] or extra:
                row.append(line["direction"])
            if extra:
                row.append(extra)
            lines.append(row)
        compact.append({**page, "lines": lines})
    result["pages"] = compact
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "build"):
        command = sub.add_parser(name)
        command.add_argument("--source", required=True)
        command.add_argument("--output", required=True)
        command.add_argument("--render-dir")
        if name == "inspect":
            command.add_argument("--pages")
        else:
            command.add_argument("--plan", required=True)
            command.add_argument("--report", required=True)
            command.add_argument("--font")
    viewer = sub.add_parser("view", help="Read existing JSON without modifying it")
    viewer.add_argument("--input", required=True)
    viewer.add_argument("--kind", choices=("inventory", "report"), required=True)
    viewer.add_argument("--pages")
    viewer.add_argument("--detail", choices=("compact", "full"), default="compact")
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            result = inspect_pdf(args.source, args.output, args.pages, args.render_dir)
            print(json.dumps({"status": "inspected", "pages": len(result["pages"]), "output": args.output}))
        elif args.command == "view":
            result = view_data(args.input, args.kind, args.pages, args.detail)
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        else:
            result = build_pdf(args.source, args.plan, args.output, args.report, args.font, args.render_dir)
            print(json.dumps({"status": result["status"], "pages": len(result["pages"]), "output": args.output}))
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
