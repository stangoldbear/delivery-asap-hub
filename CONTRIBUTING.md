# Contributing

Thanks for looking at the code. This is a small tool with a deliberately small
surface: the guidance below is mostly about what *not* to add.

## How this repository is published

This repository is a **published snapshot**. Development happens in a separate
private workspace and every release lands here as a single commit, so the
history is one entry per version rather than a stream of working commits.

That has one practical consequence: a pull request cannot be merged here
directly. Open one anyway, or open an issue — patches are applied upstream and
ship in the following release, with attribution in the changelog. Bug reports
and design discussion are just as welcome as code.

## Running it

```bash
python3 dashboard.py --vault sample-vault --port 8099
python3 -m unittest test_dahub -v
```

Python 3.11 or newer, no dependencies, no build step. Adding a dependency needs
a reason that a few lines of the standard library cannot cover.

## Invariants

These are the rules that keep the codebase small. Breaking one is how a
500-line module becomes a 5,000-line one.

1. **Only `repository` touches the filesystem.** `domain` is pure: no file
   access, and no `date.today()` or `datetime.now()` buried inside it — the
   clock is passed in, which is what makes the timeline testable.
2. **Python never emits CSS or JavaScript.** `dahub/static/app.css` and
   `app.js` are real files. Values reach the browser as escaped text or escaped
   `data-*` attributes, never interpolated into executable code.
3. **Layout metrics have one home.** `settings.py` declares them and the view
   emits them as CSS custom properties. If you find yourself writing `340` in
   the stylesheet or in the script, stop.
4. **The card schema is declared once**, in `dahub/schema.py`. The API
   validates and applies from it; the browser renders the Advanced Edit form
   from the same declaration, served at `/api/schema`.
5. **Validate at the boundary.** An unknown `status`, `tier` or `severity` is
   refused with a 400 before it can reach a file. Never let an invalid value
   land in the vault to be normalised later.
6. **Writes are atomic.** Go through `repository.write_atomic`; a half-written
   card is a destroyed card.
7. **Unknown keys in a card survive.** Someone's private field must not be
   deleted by a save it was not part of.

## Where to change what

| Goal | Where |
|---|---|
| add a card field | `dahub/schema.py` — one entry; form and API follow |
| add an API action | register a function in `dahub/api.ROUTES` |
| add a tier, role, squad, project code | `settings.toml` |
| change a colour or a metric | `settings.py` for constants, `settings.toml` for tiers |
| change the wording of the chrome | `settings.toml`, `[app]` |

## The vault format

A project card is markdown with YAML front matter. The reader supports the
subset the cards use — nested maps, lists of scalars, lists of single-level
maps, block scalars (`|`, `|-`, `>`), inline `# comments` and quoted strings.
Anything richer is refused or flattened, so do not reach for it.

```yaml
---
id: project-1-navigation-menu     # must match the file name
name: Navigation menu — second level
tier: tier-1                      # a key declared in settings.toml
priority: 1                       # rank inside the tier, set by drag & drop
status: active                    # active | blocked | inactive
intro: |-
  Free-form context. Not actions.
dates:
  target_delivery: 2026-11-14
  deadline_text: 2026-11-14       # what the chart badge shows; free text is fine
  deadline_type: hard             # soft | hard
tech_footprint:
  platforms: [iOS, Android, QA]
  qa_effort: medium               # low | medium | high
  content_impact: true
dependencies:
  upstream:   [{ project_or_service: …, team: …, contact: …, criticality: high }]
  downstream: [{ project_or_service: …, team: … }]
risks_and_criticalities:
  - { id: RISK-01, description: …, severity: high, mitigation: …, owner: … }
jira: { request: NIMBUS-1042, epics: [NIMBUS-1043] }
todos: [{ id: …, text: …, deadline: …, done: false }]
---
```

The delivery plan is a mermaid `gantt` block. `section` must match a
`[[squads]]` section for names to resolve; a label carrying a project code
(`P1`, …) attaches the task to that card, and anything else becomes a
stand-alone row in the last tier. `done` marks time off.

## Before you send a patch

- `python3 -m unittest test_dahub` passes, and new behaviour has a test.
  `sample-vault/` is the fixture — extend it rather than inventing a new one.
- `node --check dahub/static/app.js` if you touched the script.
- Keep the diff proportionate to the problem. A fix that also reorganises three
  modules is two changes, and only one of them was asked for.
