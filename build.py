#!/usr/bin/env python3
"""Build the Aging-in-Place Comfort Guide static site.

Converts docs/*.md into site/*.html with a shared layout and stylesheet.
No third-party dependencies: pure Python 3 standard library.

Usage:
    python3 build.py            # build the site
    python3 build.py --check    # build to a temp dir and verify result
"""

from __future__ import annotations

import html
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"
ASSETS_DIR = ROOT / "assets"
SITE_DIR = ROOT / "site"

# Reading order for the sidebar navigation and index page.
PAGE_ORDER = [
    "index",
    "room-by-room",
    "checklist",
    "weekend-fall-fixes",
    "safety-upgrades",
    "medication-systems",
    "life-alert",
    "family-conversations",
    "assisted-living",
    "cost-worksheet",
    "glossary",
]

SITE_TITLE = "The Aging-in-Place Comfort Guide"
SITE_TAGLINE = "A gentle manual for making a home work for staying independent."


# ---------------------------------------------------------------------------
# Inline markdown -> HTML
# ---------------------------------------------------------------------------

_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def render_inline(text: str) -> str:
    """Render inline markdown (code, bold, italic, links) in one line."""
    # Escape everything first so the source markup is treated as text.
    escaped = html.escape(text, quote=False)
    placeholders: list[str] = []

    def stash(html_snippet: str) -> str:
        placeholders.append(html_snippet)
        return f"\x00{len(placeholders) - 1}\x00"

    escaped = _INLINE_CODE_RE.sub(
        lambda m: stash(f"<code>{m.group(1)}</code>"), escaped
    )
    escaped = _LINK_RE.sub(
        lambda m: stash(
            f'<a href="{_rewrite_md_link(html.escape(m.group(2), quote=True))}">'
            f"{m.group(1)}</a>"
        ),
        escaped,
    )
    escaped = _BOLD_RE.sub(lambda m: stash(f"<strong>{m.group(1)}</strong>"), escaped)
    escaped = _ITALIC_RE.sub(lambda m: stash(f"<em>{m.group(1)}</em>"), escaped)

    # Nested placeholders (e.g. code inside a bold span) need repeated
    # passes: each pass can reveal placeholder tokens inside earlier
    # replacements, so loop until no control-character tokens remain.
    passes = 0
    while "\x00" in escaped and passes < 50:
        passes += 1
        for i, snippet in enumerate(placeholders):
            escaped = escaped.replace(f"\x00{i}\x00", snippet)
    if "\x00" in escaped:
        raise ValueError("inline markdown placeholder did not resolve")
    return escaped


def _rewrite_md_link(href: str) -> str:
    """Point internal .md links at the generated .html pages."""
    if re.fullmatch(r"[A-Za-z0-9_-]+\.md(?:#[^)]*)?", href):
        return re.sub(r"\.md", ".html", href)
    return href


# ---------------------------------------------------------------------------
# Block-level markdown -> HTML
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+\s*)?$")
_HR_RE = re.compile(r"^(\s*-{3,}\s*|\s*\*{3,}\s*|\s*_{3,}\s*)$")
_UL_ITEM_RE = re.compile(r"^\s*[-*]\s+(.*)$")
_OL_ITEM_RE = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
_CHECKBOX_RE = re.compile(r"^\[([ xX])\]\s+(.*)$")
_QUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_TABLE_DIVIDER_ALLOWED = set(": -|")


def _is_table_divider(row: str) -> bool:
    cells = [c.strip() for c in row.strip("|").split("|")]
    return bool(cells) and all(c and set(c) <= _TABLE_DIVIDER_ALLOWED for c in cells)


def _split_row(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _render_list(items: list[tuple[str, str | None]], ordered: bool) -> str:
    """Render list items; item text may carry a checkbox flag."""
    lines = []
    opened = False
    list_tag = "ol" if ordered else "ul"
    for text, checked in items:
        if not opened:
            cls = ' class="checklist"' if not ordered and checked is not None else ""
            lines.append(f"<{list_tag}{cls}>")
            opened = True
        if checked is None:
            lines.append(f"<li>{text}</li>")
        else:
            done = " checked" if checked else ""
            lines.append(
                f'<li><label><input type="checkbox" disabled{done}> {text}</label></li>'
            )
    if opened:
        lines.append(f"</{list_tag}>")
    return "\n".join(lines)


def render_markdown(text: str) -> str:
    """Convert a block of markdown to HTML. Supports the subset used in docs/."""
    out: list[str] = []
    lines = text.splitlines()
    i = 0
    para: list[str] = []

    def flush_paragraph() -> None:
        nonlocal para
        if para:
            joined = "<br>\n".join(render_inline(l) for l in para)
            out.append(f"<p>{joined}</p>")
            para = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Fenced code blocks
        if stripped.startswith("```"):
            flush_paragraph()
            i += 1
            code: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            continue

        # Blank line
        if not stripped:
            flush_paragraph()
            i += 1
            continue

        # Horizontal rule
        if _HR_RE.match(stripped) and "#" not in line[:5]:
            flush_paragraph()
            out.append("<hr>")
            i += 1
            continue

        # Heading
        m = _HEADING_RE.match(stripped)
        if m:
            flush_paragraph()
            level = len(m.group(1))
            level = min(max(level, 1), 6)
            out.append(
                f'<h{level} id="{_slug(m.group(2))}">{render_inline(m.group(2))}</h{level}>'
            )
            i += 1
            continue

        # Blockquote
        if _QUOTE_RE.match(line):
            flush_paragraph()
            quote: list[str] = []
            while i < len(lines) and _QUOTE_RE.match(lines[i]):
                qm = _QUOTE_RE.match(lines[i])
                quote.append(qm.group(1))
                i += 1
            quote_html = render_markdown("\n".join(quote)) or "<p></p>"
            out.append(f"<blockquote>{quote_html}</blockquote>\n")
            continue

        # Table
        if _TABLE_ROW_RE.match(line) and i + 1 < len(lines) and _is_table_divider(lines[i + 1]):
            flush_paragraph()
            header = _split_row(_TABLE_ROW_RE.match(line).group(1))
            aligns = [""] * len(header)
            align_cells = _split_row(_TABLE_ROW_RE.match(lines[i + 1]).group(1))
            for j, cell in enumerate(align_cells[: len(header)]):
                if cell.startswith(":") and cell.endswith(":"):
                    aligns[j] = ' style="text-align:center"'
                elif cell.endswith(":"):
                    aligns[j] = ' style="text-align:right"'
                elif cell.startswith(":"):
                    aligns[j] = ' style="text-align:left"'
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and _TABLE_ROW_RE.match(lines[i]):
                rows.append(_split_row(_TABLE_ROW_RE.match(lines[i]).group(1)))
                i += 1
            t = ['<div class="tablewrap"><table>', "<thead><tr>"]
            for j, cell in enumerate(header):
                t.append(f"<th{aligns[j]}>{render_inline(cell)}</th>")
            t.append("</tr></thead>")
            if rows:
                t.append("<tbody>")
                for row in rows:
                    t.append("<tr>")
                    for j in range(len(header)):
                        cell = row[j] if j < len(row) else ""
                        t.append(f"<td{aligns[j]}>{render_inline(cell)}</td>")
                    t.append("</tr>")
                t.append("</tbody>")
            t.append("</table></div>")
            out.append("\n".join(t))
            continue

        # Ordered list
        if _OL_ITEM_RE.match(line):
            flush_paragraph()
            items: list[tuple[str, str | None]] = []
            while i < len(lines) and (_OL_ITEM_RE.match(lines[i]) or (lines[i].strip() and lines[i].startswith("  "))):
                om = _OL_ITEM_RE.match(lines[i])
                if om:
                    items.append((render_inline(om.group(2)), None))
                else:
                    # continuation line joins the previous item
                    if items:
                        text_prev, _ = items[-1]
                        items[-1] = (text_prev + " " + render_inline(lines[i].strip()), None)
                i += 1
            out.append(_render_list(items, ordered=True) + "\n")
            continue

        # Unordered list (with optional checkbox items)
        if _UL_ITEM_RE.match(line):
            flush_paragraph()
            ul_items: list[tuple[str, str | None]] = []
            while i < len(lines) and (_UL_ITEM_RE.match(lines[i]) or (lines[i].strip() and lines[i].startswith("  "))):
                um = _UL_ITEM_RE.match(lines[i])
                if um:
                    cm = _CHECKBOX_RE.match(um.group(1))
                    if cm:
                        ul_items.append((render_inline(cm.group(2)), cm.group(1).lower() == "x"))
                    else:
                        ul_items.append((render_inline(um.group(1)), None))
                else:
                    if ul_items:
                        text_prev, flag = ul_items[-1]
                        ul_items[-1] = (text_prev + " " + render_inline(lines[i].strip()), flag)
                i += 1
            out.append(_render_list(ul_items, ordered=False) + "\n")
            continue

        # Paragraph (may wrap; blank lines end it)
        if para and (stripped.startswith(("**", "*", "_", "`")) or line.startswith("  ")):
            para.append(stripped)
        else:
            flush_paragraph()
            para = [stripped]
        i += 1

    flush_paragraph()
    return "\n".join(out)


def _slug(title: str) -> str:
    s = re.sub(r"<[^>]+>", "", title)
    s = re.sub(r"[^A-Za-z0-9\s-]", "", s).strip().lower()
    return re.sub(r"[\s]+", "-", s) or "section"


# ---------------------------------------------------------------------------
# Page plumbing
# ---------------------------------------------------------------------------


def page_title(markdown_source: str) -> str:
    for line in markdown_source.splitlines():
        m = _HEADING_RE.match(line.strip())
        if m and len(m.group(1)) == 1:
            return m.group(2)
    return "Untitled"


def load_pages(docs_dir: Path = DOCS_DIR) -> list[dict]:
    pages = []
    for slug in PAGE_ORDER:
        path = docs_dir / f"{slug}.md"
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        pages.append(
            {
                "slug": slug,
                "title": page_title(source),
                "source": source,
                "html": render_markdown(source),
            }
        )
    return pages


def build_nav(pages: list[dict], current_slug: str) -> str:
    items = []
    for p in pages:
        cls = ' aria-current="page" class="active"' if p["slug"] == current_slug else ""
        href = "index.html" if p["slug"] == "index" else f"{p['slug']}.html"
        items.append(f'<li><a href="{href}"{cls}>{html.escape(p["title"], quote=False)}</a></li>')
    return "\n".join(items)


def prev_next(pages: list[dict], current_slug: str) -> tuple[dict | None, dict | None]:
    slugs = [p["slug"] for p in pages]
    idx = slugs.index(current_slug)
    prev = pages[idx - 1] if idx > 0 else None
    nxt = pages[idx + 1] if idx < len(pages) - 1 else None
    return prev, nxt


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{tagline}">
<title>{page_title} — {site_title}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <p class="brand">{site_title}</p>
  <p class="tagline">{tagline}</p>
  <p class="notice">Practical home &amp; organization help only — never medical advice.</p>
</header>
<div class="shell">
<nav aria-label="Guide contents" class="sidebar">
<h2 class="nav-heading">Guide contents</h2>
<ul>
{nav}
</ul>
<p class="nav-foot">Local-first. No tracking.<br>© 2026 Asdale Dynamics, LLC</p>
</nav>
<main id="main">
{body}
<nav class="pagenav" aria-label="Previous and next pages">
{prev_link}{next_link}
</nav>
</main>
</div>
<footer class="site-footer">
<p>{site_title} · {tagline}</p>
<p>Complements the Caregiver Coordination Guide. Built as a static site; every page works offline.</p>
<p>© 2026 Asdale Dynamics, LLC · Released under the MIT License.</p>
</footer>
</body>
</html>
"""


def build_site(docs_dir: Path = DOCS_DIR, assets_dir: Path = ASSETS_DIR, out_dir: Path = SITE_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = load_pages(docs_dir)
    if not pages:
        raise RuntimeError("No markdown pages found in docs/")
    for p in pages:
        b = p["html"]
        if p["slug"] == "index":
            b = add_link_cards(pages)
        prev, nxt = prev_next(pages, p["slug"])
        prev_link = (
            f'<a class="pn prev" href="{_href(prev["slug"])}">← {html.escape(prev["title"], quote=False)}</a>'
            if prev
            else "<span></span>"
        )
        next_link = (
            f'<a class="pn next" href="{_href(nxt["slug"])}">{html.escape(nxt["title"], quote=False)} →</a>'
            if nxt
            else "<span></span>"
        )
        page = TEMPLATE.format(
            site_title=SITE_TITLE,
            tagline=SITE_TAGLINE,
            page_title=html.escape(p["title"], quote=False),
            nav=build_nav(pages, p["slug"]),
            body=b,
            prev_link=prev_link,
            next_link=next_link,
        )
        target = out_dir / ("index.html" if p["slug"] == "index" else f"{p['slug']}.html")
        target.write_text(page, encoding="utf-8")
    css_src = assets_dir / "style.css"
    if css_src.exists():
        shutil.copy(css_src, out_dir / "style.css")
    return sorted(out_dir.glob("*.html"))


def _href(slug: str) -> str:
    return "index.html" if slug == "index" else f"{slug}.html"


def add_link_cards(pages: list[dict]) -> str:
    """Card grid of all guide sections appended to the index page body."""
    cards = []
    for p in pages:
        if p["slug"] == "index":
            continue
        cards.append(
            f'<a class="card" href="{_href(p["slug"])}"><strong>{html.escape(p["title"], quote=False)}</strong></a>'
        )
    grid = "\n".join(cards)
    return (
        '<div class="cardgrid" aria-label="Guide sections">\n' + grid + "\n</div>\n"
        + '<p class="smallprint">Tip: each page links to the next, so you can read straight through like a book.</p>'
    )


def main(argv: list[str]) -> int:
    if "--check" in argv:
        with tempfile.TemporaryDirectory() as tmp:
            build_site(out_dir=Path(tmp))
            files = sorted(Path(tmp).glob("*.html"))
            if not files:
                print("VERIFICATION FAILED: no HTML output", file=sys.stderr)
                return 1
            print(f"check ok: built {len(files)} pages into a temp dir")
            return 0
    out = build_site()
    print(f"Built {len(out)} pages + {len(list((SITE_DIR).glob('*')))} files into {SITE_DIR}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
