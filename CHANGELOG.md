# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[semantic versioning](https://semver.org/).

## 1.0.0 — 2026-09-10

First public release.

### What it does

- Renders a vault of markdown project cards as an interactive Gantt chart:
  tiers, projects ordered by priority, and one row per assigned person.
- Edits the cards back: status, deadlines, platforms, Jira/Confluence/Figma
  links, free-form notes and an action list with history — saved straight into
  the markdown file.
- Covers the whole card schema through an Advanced Edit panel, in a form or as
  raw text, with the raw text validated before it can reach the file.
- Reorders projects by drag and drop, and collapses the chart to the days from
  today onwards.

### Notable properties

- **No dependency and no build step**: Python 3.11+ standard library, one
  stylesheet, one script.
- **Configuration, not code**: tiers, squads, roles, project codes, links and
  wording live in `settings.toml`. Running it for a different team needs no
  Python edit.
- **The card schema is declared once** and drives the API, its validation and
  the browser form alike.
- **Invalid input is refused at the boundary** with a 400 rather than stored
  and normalised later, and a stored invalid value is shown as such instead of
  being silently replaced.
- **Writes are atomic** and unknown keys in a card are preserved, so a save
  cannot truncate or quietly prune your file.
- **Loopback by default**, with a content security policy and no external
  request: it works offline.
- 53 tests over a fictional sample vault that exercises every rendering,
  parsing and failure path.
