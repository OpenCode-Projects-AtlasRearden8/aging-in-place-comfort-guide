# STATUS.md — Aging-in-Place Comfort Guide

Last updated: 2026-10-31

## What was built

A complete, local-first static guide for staying independent at home — practical and administrative help only, never medical advice. 11 markdown pages in `docs/` build into a tested static HTML site.

**Content (docs/):**

- `index.md` — start-here overview, three principles, how the guide fits together
- `room-by-room.md` — room-by-room walkthrough (street-to-basement) of a real home
- `checklist.md` — printable walk-through checklist with checkbox lists and a scoring section
- `weekend-fall-fixes.md` — fall-risk fixes split into 7 self-contained weekend doses
- `safety-upgrades.md` — grab bars, lighting, and upgrades in a justified order, with a budget-snapshot table
- `medication-systems.md` — pill, appointment, and paper systems designed for bad days (organizational only)
- `life-alert.md` — PERS/home/mobile/smartwatch options decoded, feature glossary, 10-question buying checklist
- `family-conversations.md` — scripts and logistics for talking family through changes without fights
- `assisted-living.md` — due-diligence guide: what it is, honest signals, comparison table, facility-visit checklist
- `cost-worksheet.md` — upgrade-cost planning worksheet (one-time, ongoing, "the only sentence that matters")
- `glossary.md` — plain-English glossary of guide terms, invoice terms, and facility terms

**Tooling:**

- `build.py` — dependency-free (stdlib only) markdown→HTML static-site generator with shared nav, prev/next links, index card grid, and `--check` mode
- `assets/style.css` — accessible, large-type stylesheet (skip link, semantic HTML, responsive under 56rem)
- `tests/test_build.py` — 24 unittest cases covering inline/block markdown rendering, link rewriting, HTML escaping, site assembly, idempotency, and end-to-end invariants (all internal links resolve, no stray control bytes)
- `site/` — generated output, committed so the folder works with zero tooling (just open `site/index.html`)
- `LICENSE` — MIT, `Copyright (c) 2026 Asdale Dynamics, LLC`, credited in README
- Companion reference to the caregiver-coordination-guide (schedule/task side of the same household)

## How to run it

```bash
python3 build.py                             # (re)build site/ from docs/
python3 build.py --check                     # rebuild into a temp dir and verify
python3 -m unittest discover -s tests -v     # run the test suite
```

Then open `site/index.html` in any browser. Everything works offline; nothing leaves the machine.

## Verification results (2026-10-31)

- `python3 build.py` → "Built 11 pages + 12 files into site/" — OK
- `python3 build.py --check` → "check ok: built 11 pages into a temp dir" — OK
- `python3 -m unittest discover -s tests` → **Ran 24 tests … OK** (0 failures)
- End-to-end checks in the suite verify: every internal `.md` link resolves to a generated `.html` page, output is byte-identical on rebuild (idempotent), HTML escaping prevents injected markup, and no stray control/NUL bytes in output
- Secret/personal-data scan over md/py/html/css: no API keys, credentials, emails, or personal data (verified; the only regex hits were false positives such as "ri·sk-f·ixes")

## Known gaps

- The markdown engine is deliberately a small subset (headings, paragraphs, lists, checkboxes, tables, quotes, fenced code, inline emphasis/links/code, `---`). It is tested for exactly what docs/ uses — not a general-purpose parser. Nested markdown in table cells is not supported.
- Prices are rounded planning ranges (US-oriented, current as of writing); no data files are bundled for cost lookups — the worksheet is fill-in-your-own.
- The Caregiver Coordination Guide is referenced but lives in its own project; there is no cross-repo link automation.
- No JavaScript features by design (print and read only); no print stylesheet beyond the browser default.
- No multi-language versions yet.
