"""Tests for the Aging-in-Place Comfort Guide build.

Run with:
    python3 -m unittest discover -s tests -v
"""

import re
import tempfile
import unittest
from pathlib import Path

import build as b

ROOT = Path(__file__).resolve().parent.parent


class InlineMarkdownTests(unittest.TestCase):
    def test_bold(self):
        self.assertEqual(b.render_inline("**hi**"), "<strong>hi</strong>")

    def test_italic(self):
        self.assertEqual(b.render_inline("*softly*"), "<em>softly</em>")

    def test_code_span(self):
        self.assertEqual(b.render_inline("`x = 1`"), "<code>x = 1</code>")

    def test_link_and_bold_combined(self):
        self.assertEqual(
            b.render_inline("**a** [t](room-by-room.md)"),
            "<strong>a</strong> <a href=\"room-by-room.html\">t</a>",
        )

    def test_escape_is_safe(self):
        out = b.render_inline('<script>alert("x")</script>')
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_md_link_rewritten(self):
        out = b.render_inline("[go](glossary.md)")
        self.assertIn('href="glossary.html"', out)

    def test_external_link_untouched(self):
        out = b.render_inline("[go](https://example.org)")
        self.assertIn('href="https://example.org"', out)

    def test_no_static_placeholder_bytes(self):
        out = b.render_inline("*a* `b` **c** [d](e.md)")
        self.assertNotIn("\x00", out)


class BlockMarkdownTests(unittest.TestCase):
    def test_heading_levels_and_ids(self):
        out = b.render_markdown("## Two\n## Two again")
        self.assertIn('<h2 id="two">', out)
        self.assertIn('<h2 id="two-again">', out)

    def test_paragraph(self):
        out = b.render_markdown("One line")
        self.assertIn("<p>One line</p>", out)

    def test_unordered_list(self):
        out = b.render_markdown("- a\n- b")
        self.assertIn("<ul>", out)
        self.assertEqual(out.count("<li>"), 2)

    def test_ordered_list(self):
        out = b.render_markdown("1. a\n2. b")
        self.assertIn("<ol>", out)
        self.assertEqual(out.count("<li>"), 2)

    def test_checklist(self):
        out = b.render_markdown("- [ ] todo\n- [x] done")
        self.assertIn('class="checklist"', out)
        self.assertIn('type="checkbox" disabled', out)
        self.assertIn(" checked", out)
        self.assertEqual(out.count("<li>"), 2)

    def test_blockquote(self):
        out = b.render_markdown("> quoted\n> more")
        self.assertIn("<blockquote>", out)
        self.assertIn("quoted", out)

    def test_table(self):
        out = b.render_markdown("| a | b |\n| --- | --- |\n| 1 | 2 |")
        self.assertIn("<table>", out)
        self.assertIn("<th", out)
        self.assertIn("<td>1</td>", out)

    def test_horizontal_rule(self):
        self.assertIn("<hr>", b.render_markdown("para\n\n---\n\nmore"))

    def test_fenced_code_is_escaped(self):
        out = b.render_markdown("```\n<b>&raw</b>\n```")
        self.assertIn("<pre><code>", out)
        self.assertIn("&lt;b&gt;", out)

    def test_hr_regex_edge(self):
        out = b.render_markdown("- item\n\n---")
        self.assertIn("<hr>", out)


class PagePlumbingTests(unittest.TestCase):
    def test_page_title_picks_h1(self):
        self.assertEqual(b.page_title("# Hello\n\nbody"), "Hello")

    def test_page_title_fallback(self):
        self.assertEqual(b.page_title("no heading here"), "Untitled")


class SiteBuildTests(unittest.TestCase):
    def _fixture_docs(self, docs_dir: Path) -> None:
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "index.md").write_text(
            "# Guide Home\n\nWelcome to [glossary](glossary.md).\n", encoding="utf-8"
        )
        (docs_dir / "glossary.md").write_text("# Glossary\n\n- term: meaning\n", encoding="utf-8")

    def test_build_produces_pages_and_links_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            docs = tmp / "docs"
            out = tmp / "site"
            self._fixture_docs(docs)
            # Strip assets dir reliance: build reads assets from repo path by default
            pages = b.build_site(docs_dir=docs, assets_dir=ROOT / "assets", out_dir=out)
            names = [p.name for p in pages]
            self.assertIn("index.html", names)
            self.assertIn("glossary.html", names)
            html = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="glossary.html"', html)
            # Every internal .html link points at an existing file
            for page in pages:
                text = page.read_text(encoding="utf-8")
                for href in re.findall(r'href="([A-Za-z0-9_-]+\.html)"', text):
                    self.assertTrue(
                        (out / href).exists(),
                        f"{page.name} links to missing {href}",
                    )
            # Nav present and current page marked
            self.assertIn("aria-current", html)

    def test_build_over_existing_output_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            docs = tmp / "docs"
            self._fixture_docs(docs)
            b.build_site(docs_dir=docs, assets_dir=ROOT / "assets", out_dir=tmp / "site")
            first = (tmp / "site" / "index.html").read_bytes()
            b.build_site(docs_dir=docs, assets_dir=ROOT / "assets", out_dir=tmp / "site")
            second = (tmp / "site" / "index.html").read_bytes()
            self.assertEqual(first, second)


class RealDocsBuildTests(unittest.TestCase):
    """Build the actual docs/ and check invariants end to end."""

    def test_full_site_builds_with_no_stray_control_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "site"
            pages = b.build_site(out_dir=out)
            self.assertEqual(len(pages), len(b.PAGE_ORDER))
            self.assertIn("style.css", [p.name for p in out.iterdir()])
            for page in out.glob("*.html"):
                data = page.read_bytes()
                for bad in (b"\x00", b"\x0b", b"\x0c"):
                    self.assertNotIn(bad, data, f"{page.name} contains stray byte {bad!r}")
                text = page.read_text(encoding="utf-8")
                self.assertIn("Asdale Dynamics, LLC", text)
                self.assertIn("never medical advice", text.replace("&amp;", "&"))
            # All real docs are linked somewhere in the site
            all_html = "\n".join(p.read_text(encoding="utf-8") for p in out.glob("*.html"))
            for p in pages:
                self.assertIn((out / (p.stem if p.stem != "index" else "index")).name, all_html)

    def test_doc_pages_link_each_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "site"
            b.build_site(out_dir=out)
            body = (out / "index.html").read_text(encoding="utf-8")
            for slug in ("room-by-room", "checklist", "weekend-fall-fixes"):
                self.assertIn(f"{slug}.html", body)


if __name__ == "__main__":
    unittest.main()
