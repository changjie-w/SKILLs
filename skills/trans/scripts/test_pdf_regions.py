#!/usr/bin/env python3
"""Local regression tests. Synthetic inputs only; no Zotero or network access."""
import copy
import json
from pathlib import Path
import random
import tempfile
import unittest
import subprocess
import sys

import pymupdf as fitz
from pdf_regions import LayoutError, build_pdf, digest, inspect_pdf, normalized, pixels, put_translation, verify_output, view_data


def make_fixture(directory):
    directory = Path(directory)
    source = directory / "source.pdf"
    doc = fitz.open()
    page = doc.new_page(width=300, height=420)
    page.insert_text((20, 24), "A paper title", fontsize=14)
    page.insert_text((20, 43), "Alice, Example University", fontsize=8)
    page.insert_text((20, 65), "We keep x fixed [1].", fontsize=10)
    page.insert_text((20, 98), "V(s) = r + 0.9 V(s')", fontsize=10)
    page.insert_text((20, 126), "The formula stays here.", fontsize=9)
    page.draw_rect((170, 50, 275, 115), color=(0, 0, 1), fill=(.9, .95, 1))
    page.draw_line((175, 110), (265, 58), color=(1, 0, 0))
    page.insert_text((178, 90), "Figure data: 42", fontsize=8)
    page.insert_text((165, 143), "Figure 1: Results.", fontsize=8)
    page.insert_text((20, 240), "REFERENCES", fontsize=12)
    page.insert_text((20, 258), "[1] Smith. A Study. 2024. doi:example", fontsize=8)
    page = doc.new_page(width=360, height=240)
    page.insert_text((20, 40), "REFERENCES", fontsize=12)
    page.insert_text((20, 70), "[2] Lee. Another Study. 2025.", fontsize=10)
    page = doc.new_page(width=420.5, height=297.25)
    page.insert_text((25, 45), "Appendix A", fontsize=12)
    page.insert_text((25, 80), "A second page size and a formula.", fontsize=10)
    page.insert_text((25, 130), "a + b = c", fontsize=10)
    page = doc.new_page(width=320, height=210)
    page.insert_text((20, 40), "REFERENCES - rotated page", fontsize=10)
    page.set_rotation(90)
    doc.save(source)
    doc.close()
    plan = {"version": 1, "source_sha256": digest(source), "pages": [
        {"source_page": 1, "mode": "translate", "translations": [
            {"id": "title", "kind": "title", "rect": [18, 5, 280, 32], "text": "论文标题", "font_size": 14},
            {"id": "body", "rect": [18, 49, 150, 78], "text": "我们保持 x 不变 [1]。"},
            {"id": "after-eq", "rect": [18, 112, 150, 155], "text": "公式保留在原来的位置。"},
            {"id": "caption", "kind": "caption", "for": "fig-1", "rect": [160, 125, 280, 165], "text": "图 1：实验结果。"}],
         "preserve": [
            {"id": "authors", "kind": "authors", "rect": [18, 33, 155, 47]},
            {"id": "eq-1", "kind": "formula", "rect": [18, 80, 150, 109]},
            {"id": "fig-1", "kind": "figure", "rect": [165, 48, 280, 119]},
            {"id": "refs", "kind": "references", "rect": [18, 220, 282, 280]}]},
        {"source_page": 2, "mode": "copy", "reason": "references"},
        {"source_page": 3, "mode": "translate", "translations": [
            {"id": "heading", "kind": "heading", "rect": [20, 25, 380, 58], "text": "附录 A", "font_size": 12},
            {"id": "body", "rect": [20, 65, 380, 105], "text": "这里使用另一种页面尺寸，并保留公式。"}],
         "preserve": [{"id": "eq", "kind": "formula", "rect": [20, 110, 380, 145]}]},
        {"source_page": 4, "mode": "copy", "reason": "references"}
    ]}
    return source, plan


class RegionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="trans-test-")
        self.root = Path(self.temp.name)
        self.source, self.plan = make_fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def build(self, plan=None, font=None):
        path = self.root / "plan.json"
        path.write_text(json.dumps(plan or self.plan, ensure_ascii=False), encoding="utf-8")
        return build_pdf(self.source, path, self.root / "result.pdf", self.root / "report.json", font)

    def test_mixed_sizes_references_formula_and_search(self):
        original = self.source.read_bytes()
        report = self.build()
        self.assertEqual(report["status"], "file_checks_passed")
        self.assertEqual(self.source.read_bytes(), original)
        with fitz.open(self.root / "result.pdf") as doc:
            self.assertEqual(len(doc), 4)
            self.assertEqual(doc[2].rect.width, 841)
            self.assertEqual(doc[3].rect.width, 420)
            self.assertIn("论文标题", normalized(doc[0].get_text()))
            self.assertIn("V(s)=r+0.9V(s')", normalized(doc[0].get_text()))
            self.assertNotIn("中", doc[1].get_text())

    def test_overflow_has_page_and_region_and_no_pdf(self):
        plan = copy.deepcopy(self.plan)
        plan["pages"][0]["translations"][1]["text"] = "不能删去这些内容。" * 500
        with self.assertRaisesRegex(LayoutError, r"source page 1: region body: overflow"):
            self.build(plan)
        self.assertFalse((self.root / "result.pdf").exists())
        self.assertEqual(json.loads((self.root / "report.json").read_text())["status"], "failed")

    def test_protected_overlap_is_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["pages"][0]["translations"][1]["rect"] = [18, 49, 150, 100]
        with self.assertRaisesRegex(LayoutError, "overlaps"):
            self.build(plan)

    def test_missing_caption_target_is_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["pages"][0]["translations"][-1]["for"] = "missing"
        with self.assertRaisesRegex(LayoutError, "matching figure"):
            self.build(plan)

    def test_missing_page_is_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["pages"].pop()
        with self.assertRaisesRegex(LayoutError, "exactly cover scope"):
            self.build(plan)

    def test_unclassified_source_is_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["pages"][0]["preserve"].pop(0)
        with self.assertRaisesRegex(LayoutError, "unclassified source"):
            self.build(plan)

    def test_inspect_and_explicit_scope(self):
        info = inspect_pdf(self.source, self.root / "inventory.json", "2,4")
        self.assertEqual([p["source_page"] for p in info["pages"]], [2, 4])
        self.assertEqual(info["pages"][1]["size"], [210, 320])
        plan = copy.deepcopy(self.plan)
        plan["scope"] = [2]
        plan["pages"] = [plan["pages"][1]]
        self.assertEqual(self.build(plan)["scope"], [2])

    def test_custom_font(self):
        # Obtain a bundled CJK font; no platform-specific font path is required.
        font = self.root / "custom.otf"
        font.write_bytes(fitz.Font("cjk").buffer)
        self.assertEqual(self.build(font=str(font))["status"], "file_checks_passed")

    def test_no_padding_fits_short_line_without_smaller_font(self):
        region = {"id": "short", "rect": [20, 20, 140.8, 33],
                  "text": "一个通信网络，其中节点", "font_size": 8.4,
                  "min_font_size": 8.4, "line_height": 1.3}
        with fitz.open() as doc:
            page = doc.new_page()
            with self.assertRaisesRegex(LayoutError, "overflow"):
                put_translation(page, region, None)
            result = put_translation(page, {**region, "no_padding": True}, None)
            self.assertTrue(result["no_padding"])
            self.assertEqual(result["font_size"], 8.4)
            self.assertEqual(normalized(page.get_text()), normalized(region["text"]))
            for block in page.get_text("dict")["blocks"]:
                self.assertTrue(fitz.Rect(region["rect"]).contains(fitz.Rect(block["bbox"])))

    def test_no_padding_build_and_true_overflow(self):
        plan = copy.deepcopy(self.plan)
        region = plan["pages"][0]["translations"][1]
        region["no_padding"] = True
        region["line_height"] = 1.3
        report = self.build(plan)
        self.assertTrue(report["pages"][0]["translations"][1]["no_padding"])
        with fitz.open() as doc:
            page = doc.new_page()
            with self.assertRaisesRegex(LayoutError, "overflow"):
                put_translation(page, {**region, "text": "完整内容" * 500}, None)

    def test_no_padding_rejects_non_boolean(self):
        with fitz.open() as doc:
            page = doc.new_page()
            with self.assertRaisesRegex(LayoutError, "no_padding must be boolean"):
                put_translation(page, {**self.plan["pages"][0]["translations"][0],
                                       "no_padding": "false"}, None)

    def test_no_padding_does_not_bypass_glyph_bounds(self):
        plan = copy.deepcopy(self.plan)
        region = plan["pages"][0]["translations"][1]
        region.update(no_padding=True, line_height=1)
        with self.assertRaisesRegex(LayoutError, "glyph extends outside region"):
            self.build(plan)
        self.assertFalse((self.root / "result.pdf").exists())


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="trans-pixels-test-")
        self.root = Path(self.temp.name)
        self.source = self.root / "source.pdf"
        with fitz.open() as doc:
            page = doc.new_page(width=595.2756, height=340.125)
            page.insert_text((20, 24), "A title", fontsize=12)
            rng = random.Random(0)
            shape = page.new_shape()
            for _ in range(100):
                shape.draw_line((rng.uniform(20, 570), rng.uniform(50, 270)),
                                (rng.uniform(20, 570), rng.uniform(50, 270)))
                shape.finish(width=.15)
            shape.commit()
            page.draw_line((40.25, 300.125), (43.25, 300.125), width=.1)
            for position, text, size in [((200, 310), "x", 10), ((205, 305), "2", 6),
                                         ((214, 310), "-", 10), ((227, 310), "42", 10)]:
                page.insert_text(position, text, fontsize=size)
            doc.save(self.source)
        self.plan = {"version": 1, "source_sha256": digest(self.source), "pages": [{
            "source_page": 1, "mode": "translate",
            "translations": [{"id": "title", "rect": [18, 5, 570, 35], "text": "标题"}],
            "preserve": [{"id": "figure", "kind": "figure", "rect": [18, 45, 580, 330]}]}]}
        plan_path = self.root / "plan.json"
        plan_path.write_text(json.dumps(self.plan, ensure_ascii=False), encoding="utf-8")
        self.output, self.report_path = self.root / "result.pdf", self.root / "report.json"
        self.report = build_pdf(self.source, plan_path, self.output, self.report_path)

    def tearDown(self):
        self.temp.cleanup()

    def test_unmodified_right_vectors_and_warning_evidence(self):
        self.assertEqual(self.report["status"], "file_checks_passed")
        self.assertEqual(self.report["source_sha256"], digest(self.source))
        with fitz.open(self.source) as source, fitz.open(self.output) as result:
            box = self.plan["pages"][0]["preserve"][0]["rect"]
            differs = pixels(source[0], box) != pixels(result[0], box, source[0].rect.width)
        warnings = [w for w in self.report["warnings"] if w["check"] == "source page 1, figure"]
        # Some renderer versions may not exhibit the original embedding artifact.
        self.assertEqual(bool(warnings), differs)
        if warnings:
            self.assertIn("Exact 72 dpi match", warnings[0]["evidence"])
        summary = view_data(self.report_path, "report")
        self.assertEqual(summary["warnings"], self.report["warnings"])
        self.assertEqual(summary["visual_review"], "not_assessed")
        self.assertEqual(summary["translation_accuracy"], "not_assessed")

    def test_actual_protected_damage_is_rejected(self):
        for kind, box in [("thin-line", [39, 299, 45, 302]), ("symbol", [213, 298, 219, 313]),
                          ("superscript", [204, 297, 210, 307]), ("chart-data", [226, 298, 240, 313]),
                          ("occlusion", [100, 120, 220, 180])]:
            with self.subTest(kind=kind), fitz.open(self.output) as damaged:
                page = damaged[0]
                width = page.rect.width / 2
                target = fitz.Rect(box) + (width, 0, width, 0)
                if kind in {"symbol", "superscript", "chart-data"}:
                    page.add_redact_annot(target, fill=(1, 1, 1))
                    page.apply_redactions(images=0, graphics=0, text=0)
                else:
                    page.draw_rect(target, color=None, fill=(1, 1, 1))
                if kind == "superscript":
                    page.insert_text((width + 205, 315), "2", fontsize=6)
                elif kind == "chart-data":
                    page.insert_text((width + 227, 310), "43", fontsize=10)
                path = self.root / f"{kind}.pdf"
                damaged.save(path)
                with fitz.open(self.source) as source, self.assertRaisesRegex(LayoutError, "figure: preserved pixels differ"):
                    verify_output(path, source, self.plan["pages"], copy.deepcopy(self.report))

    def test_displaced_or_cropped_right_content_is_rejected(self):
        for kind in ("displaced", "cropped"):
            with self.subTest(kind=kind), fitz.open(self.source) as source, fitz.open() as doc:
                original = source[0]
                width, height = original.rect.width, original.rect.height
                page = doc.new_page(width=2 * width, height=height)
                page.show_pdf_page(original.rect, source, 0)
                shift = width + (.25 if kind == "displaced" else 0)
                clip = fitz.Rect(0, 0, 230, height) if kind == "cropped" else original.rect
                page.show_pdf_page(clip + (shift, 0, shift, 0), source, 0, clip=clip)
                path = self.root / f"{kind}.pdf"
                doc.save(path)
                with self.assertRaisesRegex(LayoutError, "figure: preserved pixels differ"):
                    verify_output(path, source, self.plan["pages"], copy.deepcopy(self.report))


class ViewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="trans-view-test-")
        self.path = Path(self.temp.name) / "inventory.json"
        self.data = {"version": 1, "source": "paper.pdf", "source_sha256": "abc", "page_count": 9,
                     "pages": [{"source_page": n, "size": [420.5, 297.25], "lines": [
                         {"rect": [0.0000000000001, 2.123456789, 20.5, 50.25],
                          "direction": [1.0, 0.0], "text": "Full text, no truncation: 数值 [1] & <x>"},
                         {"rect": [30, 30, 40, 40], "direction": [0.0, -1.0], "text": "Rotated"},
                         {"rect": [50, 50, 60, 60], "direction": [1.0, 0.0], "text": "Extra", "custom": 42}],
                                "images": [[1.2, 3.4, 50.6, 70.8]], "drawings": [[1, 2, 3, 4]],
                                "future_page_field": "kept"} for n in [2, 9]]}
        self.path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        self.original = self.path.read_bytes()

    def tearDown(self):
        self.assertEqual(self.path.read_bytes(), self.original)
        self.temp.cleanup()

    def test_compact_pages_roundtrip_without_loss(self):
        view = view_data(self.path, "inventory", "2,9")
        restored = []
        for page in view["pages"]:
            lines = []
            for row in page["lines"]:
                line = {"rect": row[0], "text": row[1],
                        "direction": row[2] if len(row) > 2 else view["default_direction"]}
                if len(row) > 3:
                    line.update(row[3])
                lines.append(line)
            restored.append({**page, "lines": lines})
        self.assertEqual(restored, self.data["pages"])

    def test_index_and_selected_full(self):
        index = view_data(self.path, "inventory")
        self.assertEqual([p["source_page"] for p in index["pages"]], [2, 9])
        self.assertEqual(index["pages"][0]["counts"], {"lines": 3, "images": 1, "drawings": 1})
        self.assertEqual(view_data(self.path, "inventory", detail="full"), self.data)
        self.assertEqual(view_data(self.path, "inventory", "9", "full"),
                         {**self.data, "pages": [self.data["pages"][1]]})

    def test_unavailable_pages_and_wrong_kind_rejected(self):
        for selection in ["3", "2-9", "9,2", "2,2", "0", "oops"]:
            with self.subTest(selection=selection), self.assertRaises(LayoutError):
                view_data(self.path, "inventory", selection)
        with self.assertRaisesRegex(LayoutError, "not a build report"):
            view_data(self.path, "report")

    def test_failure_and_unassessed_checks_survive_summary(self):
        report = {"status": "failed", "error": "source page 9: region body: overflow",
                  "visual_review": "not_assessed", "translation_accuracy": "not_assessed", "scope": [2, 9],
                  "pages": [{"source_page": 2, "file_checks": "passed", "translations": [{"id": "ok"}],
                             "preserve": [{"id": "figure"}]}]}
        path = self.path.parent / "report.json"
        path.write_text(json.dumps(report))
        before = path.read_bytes()
        summary = view_data(path, "report", "2")
        for key in ("status", "error", "visual_review", "translation_accuracy", "scope"):
            self.assertEqual(summary[key], report[key])
        self.assertEqual(summary["pages"], [{"source_page": 2, "file_checks": "passed"}])
        self.assertEqual(view_data(path, "report", detail="full"), report)
        empty = self.path.parent / "early-failure.json"
        empty.write_text(json.dumps({**report, "pages": []}))
        self.assertEqual(view_data(empty, "report")["status"], "failed")
        self.assertEqual(path.read_bytes(), before)

    def test_view_cli(self):
        script = Path(__file__).with_name("pdf_regions.py")
        result = subprocess.run([sys.executable, str(script), "view", "--input", str(self.path),
                                 "--kind", "inventory", "--pages", "2"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), view_data(self.path, "inventory", "2"))
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])


if __name__ == "__main__":
    unittest.main(verbosity=2)
