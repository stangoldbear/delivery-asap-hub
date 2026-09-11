# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[semantic versioning](https://semver.org/).

## 1.0.0 — 2026-09-11

First version.

### What it does

- Renders a vault of markdown project cards as an interactive Gantt chart:
  tiers, projects ordered by a chart-wide position, and one row per assigned
  person. Every bar is declared by the card that owns it.
- Opens on today, and remembers if you would rather see the whole scale.
- Edits the cards back: name, status, deadlines, platforms,
  Jira/Confluence/Figma links, free-form notes, milestones, attachments of any
  type and an action list with history — saved straight into the vault. A value
  reads as information until you double-click it, and every editor has an
  explicit Save and Cancel.
- Moves and resizes the bars by dragging them, in whole working days.
- Reorders projects across tiers by drag and drop, finishes one by dragging it
  into DONE and abandons one by dragging it into DROPPED.
- Reorders the notes of a project the same way.
- Marks the days that matter: a milestone is a diamond on the project's lane,
  added by clicking an empty day, edited and deleted in place.
- Shows the whole vault two ways: the chart, and a Hierarchy view whose
  Structure tab lists tier → project → people and whose Markdown tab is every
  card in one editable document — the monthly snapshot, downloadable as a
  plain markdown file.
- Searches what the page shows, opens whatever hides a match and marks it.
- Renders the free text people type — headings, lists, bold, italic, code,
  links — escaped before it is transformed.
- Reflows on a phone: the page never scrolls sideways, the chart does inside
  its own container.
- Demands a shared access token when bound to anything but loopback; on
  loopback nothing changes and no secret is involved.

### The card format

A card is a markdown outline, not a file with a header: the title is the
project name, every field is a `- key: value` item, a group is two spaces
deeper, a multi-line value is a fenced block, and free text lives under
`## Notes`. Nothing is quoted and nothing is escaped. `--migrate-vault`
converts a vault written in YAML front matter, and `--import-plan` moves a
mermaid delivery plan into the cards that own its rows; both leave the source
untouched or backed up, and both refuse to run twice on the same file.

### Notable properties

- **No dependency and no build step**: Python 3.11+ standard library, one
  stylesheet, one script. The design language is shadcn/ui, ported by hand into
  custom properties — light and dark differ by one token block.
- **Configuration, not code**: tiers, squads, roles, links and wording live in
  `settings.toml`. Running it for a different team needs no Python edit.
- **The card schema is declared once** and drives the API, its validation and
  the browser form alike.
- **Invalid input is refused at the boundary** with a 400 rather than stored
  and normalised later, and a stored invalid value is shown as such instead of
  being silently replaced.
- **Writes are atomic** and unknown keys in a card are preserved, so a save
  cannot truncate or quietly prune your file. Nothing in the interface deletes
  a card, and a delete that does exist asks first, every time.
- **Loopback by default**, with a content security policy and no external
  request: it works offline.
- A test suite over a fictional sample vault that exercises every rendering,
  parsing and failure path.
