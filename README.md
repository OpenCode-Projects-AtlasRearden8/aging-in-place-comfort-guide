# The Aging-in-Place Comfort Guide

*A gentle manual for making a home work for staying independent.*

Room-by-room walkthroughs, grab bars and lighting in a sensible order, fall-risk fixes in weekend doses, medication and appointment systems that survive bad days, life-alert options decoded in plain English, scripts for talking family through changes, and a calm look at when assisted living deserves a spot at the kitchen table.

**Home & organization help only — never medical advice.** Nothing here diagnoses, prescribes, or replaces your doctor, pharmacist, or care team. Construction and electrical work should follow manufacturer instructions and local codes.

## Who it's for

Older adults who want to stay in their own homes, and the adult children, neighbors, and friends helping them do it. Written like a friend would explain it: plain English, step by step, never condescending.

## What's inside

| Page | What it covers |
| --- | --- |
| [Start here](docs/index.md) | How to use the guide, three principles |
| [Room-by-Room Walkthrough](docs/room-by-room.md) | Every room, one question: where would this trip me up? |
| [Walk-Through Checklist](docs/checklist.md) | Printable checklist for the actual walk |
| [Fall-Risk Fixes in Weekend Doses](docs/weekend-fall-fixes.md) | Six Saturday-sized projects, ordered |
| [Grab Bars & Lighting in Sensible Order](docs/safety-upgrades.md) | What to buy first and why, with budget ranges |
| [Medication & Appointment Systems](docs/medication-systems.md) | One place each, built for bad days |
| [Life-Alert Options Decoded](docs/life-alert.md) | Home-based, mobile, and smartwatch systems; a 10-question buying checklist |
| [Talking Family Through Changes](docs/family-conversations.md) | Scripts that keep the conversation boring, in the good way |
| [When Assisted Living Deserves a Look](docs/assisted-living.md) | Due diligence, not surrender; a comparison table to fill out once |
| [Upgrade-Cost Worksheet](docs/cost-worksheet.md) | One-time, ongoing, and "the only sentence that matters" |
| [Glossary](docs/glossary.md) | Plain-English definitions, sales-resistance included |

Complements the **Caregiver Coordination Guide** (task lists, visit schedules, hand-off notes on the family side) — this guide fixes the house, that one fixes the schedule.

## Build the site yourself

Local-first: pure Python 3 standard library, no dependencies, no accounts, no tracking.

```bash
python3 build.py            # build site into site/
python3 build.py --check    # verify build into a temp dir
python3 -m unittest discover -s tests -v   # run the test suite
```

Open `site/index.html` in any browser. Every page works offline once built.

## Repo layout

```
docs/           markdown source for all 11 pages
assets/         stylesheet for the generated site
site/           generated static site (committed so it works with zero tooling)
tests/          unittest suite for the markdown engine and build
build.py        dependency-free markdown -> HTML static-site generator
```

## Caring for the guide

Re-do the walk-through checklist twice a year. Prices drift, detectors expire, and houses drift back toward clutter — the guide is designed to be re-read, not just read.

## About

A practical life-admin guide published by **Asdale Dynamics, LLC** — beginner-friendly books, guides, and local-first tools, with healthcare-adjacent helpers that stay firmly on the education side of the line. © 2026 Asdale Dynamics, LLC. Released under the [MIT License](LICENSE) — copy it, print it, improve it, share it.
