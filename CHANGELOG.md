# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[semantic versioning](https://semver.org/).

## 1.1.1 — 2026-09-11

### Fixed

- The 1.1.0 notes announced an installable app — a manifest, a service worker
  and icons. None of it is in this repository: the progressive web app is a
  milestone of its own and was deliberately left out of 1.1.0, and the notes
  were not brought in line before the tag. The entry is gone, along with a
  reference to a build script that is not part of a release either. Nothing in
  the code changed.

## 1.1.0 — 2026-09-11

- Clicking a person in the label column opens the timeline row they own — who
  it belongs to, when it runs, its note — with a delete that asks first.
  Clicking a project title renames it. Both are the same small form dialog the
  milestones already used.
- The theme can be forced to light or dark from the footer, whatever the system
  says. The choice is applied before the first paint, so a forced dark theme no
  longer flashes white on every page.
- `timeline/move` becomes `timeline/save`, which also writes `who` and the note
  when the caller sends them, and `timeline/delete` removes a row.
- The four expand/collapse buttons become three levels — Groups, Projects,
  Stakeholders — which always mean the same thing whatever state the chart is
  in. The collapse state is held on the rows themselves, so folding a group no
  longer forgets which projects inside it were folded.
- The chart is drawn through a window you choose: from today, the last 30 days,
  this year, all dates, or from a date. It travels as `?from=…` and replaces
  `?hide_past=`.
- A reload keeps where you were: the window, everything collapsed or opened,
  and both scroll positions — the document's and the chart's own.
- Thirteen more themes behind **More…** in the footer, borrowed from well-known
  editors. Each one is a token block in `themes.css` and nothing else changes;
  the picker reads the list back out of that stylesheet, so there is no second
  list to keep in step.
- A thicker line at every month boundary and a thinner one at every week, down
  the whole chart and behind the bars.
- The Structure tab of the Hierarchy view shows every value a card holds, under
  the names the card uses — including keys this codebase knows nothing about,
  and the `## Notes` body — with each project foldable on its own.
- The calendar stays at the top while the rows scroll under it: the chart is a
  viewport of its own, pinned to the top of the window.
- A fourth level, **All details**, opens the notes and actions of every project
  along with everything else.
- An optional row of weekday initials under the day numbers, switched from the
  footer.
- The notes panel now reads as part of the project above it: the same tier rail
  running unbroken down the block, no gap under the row, an indent to where
  that project's people are listed, and the row itself held open-looking for as
  long as its panel is.
- Ten light themes beside the thirteen dark ones, in their own half of the
  picker. Both sets are generated from one palette table, so a theme is a
  block of tokens and never a second copy of the stylesheet.
- A zoom: Day, Week or Month. A column is always one working day — the zoom
  decides how wide it is drawn and the header says as much as it still can.
- The footer is a single line pinned to the bottom of the window, so the
  settings on it are reachable whatever the chart is doing.
- **A phone gets its own interface.** Below 900px the chart stops being the
  surface: a bottom tab bar carries Projects, Chart, Notes and More over the
  same cards, the default being a list of project cards with the span, the
  milestones and what is asking for attention. Tapping one opens that
  project's notes and actions under the card — the same panel the chart opens
  under its row, moved rather than copied, and never an overlay: **All
  details** would otherwise leave a screenful of windows to dismiss. A single
  tap opens what a double click opens on a desktop.
- On the chart tab a person's lane costs 35px instead of 49: the target is the
  row, which is as wide as the screen, rather than a 44pt button inside it.
  Nothing in the panel reaches past the right edge any more — the platform
  chips, the Add beside a heading, the ✕ that removes a link and a pasted URL
  all wrap instead — including a timeline chip, whose date range used to run
  off the right of the screen because a chip is a one-line pill on a desktop.
  A note gives its text the whole line beside the checkbox and keeps its
  delete in the corner, which is a third of the height back. Scrolling the
  timeline sideways no longer drags the panel along for the first 15px: it
  sticks where it stands, because it belongs to the project and not to the
  axis — and neither does it bounce: the rubber band slid the sticky label
  column and the panel out of step with the rows for as long as a finger was
  down. The project's tier rail stays beside the panel at any scroll offset,
  on the same pixel as the rails of the rows above it.
- On a phone the project title in the chart opens that project's notes and
  actions, under its row, the way tapping its card does in the list — opening
  one project no longer means **All details** and a page of every project's
  notes. The title renames on a desktop, where the row has room for the two
  buttons that do these things; on a phone the name is renamed from inside the
  panel, which now carries a **Rename** button in its header beside Move — on
  every screen, so the action is somewhere you can point at rather than a
  gesture you have to know.
- **Three things a phone could no longer do**, found by going through
  everything the small-screen rules hide: **Advanced edit** had no door at all
  — its only button lives on the project row, which has no room for it there —
  so it joins Rename and Move in the panel header. The **Hierarchy** page was
  a dead end: the header that carries the link back was hidden on every page,
  and the footer with the theme, the preferences and the snapshot download is
  a surface the tab bar reveals, and that page has no tab bar. The shell now
  says which of the two pages it is, and the phone's rules apply only to the
  one with the tab bar. And **notes can be reordered again**: dragging is the
  desktop's way and a finger cannot drag, so the note being edited carries Up
  and Down — which is also the first time the order could be changed from a
  keyboard.
- **The year, above the months**, on the zooms where a month cell has no room
  to print it — which is exactly where a chart crosses a new year without
  saying so.
- **A zoomed-out chart runs past the last bar.** At 2px a day the scale ended
  with the last project and left two thirds of the screen empty: a month view
  of one quarter is not a month view. Week now looks six months ahead and
  Month two years, from today, unless the window has named an end of its own —
  which still wins.
- **Settings**, from the footer, on every screen. The theme and the
  confirmations used to sit in the footer itself, which worked while there
  were three of them; they are now an overlay in three groups — Theme, The
  chart, Confirmations — and every option carries the sentence that says what
  it does.
- Two of them are new. **Tier bands** hides the group headings, and with them
  the depth level that shows nothing else — picking it while the chart is
  folded to Groups unfolds it to Projects rather than leaving an empty page.
  **Tier colours** hides the coloured rail down the left of every row, the
  marker on the band and the tint on a card's sparkline. Neither changes a
  card: the markup still says which tier a project is in.
- A date field with no value paints nothing at all on iOS — no format, no
  hint, an empty white box — so the due date of a note now carries a **Due**
  label beside it, in the add form and in the editor. It is the only thing
  that says what the box is for.
- The status pill and the deadline beside it sit on the same line again: the
  status was wrapped in an inline-block, which adds the leading of a line box
  around it, so centring the wrapper left the pill 1.3px low.
- The chart ends where its last row does: the grid lines and the today band are
  painted down the whole height of the scroller, and a notes panel is not a row
  of the chart, so the panel's cell is opaque and the green stripe no longer
  runs under a form.
- **Two soft edges say the chart continues that way**: the shadow the frozen
  label column casts once something is hidden behind it, and one on the right
  for as long as there is more timeline — which is the half a person needs
  before they try to scroll, and the reason it is not left to a scrollbar that
  a phone only draws while it moves.
- The chart runs to the edge of its card on a phone. The card's padding beside
  a scroll area was width the timeline could not use and a white band the rows
  were cut against; the toolbar keeps its inset, the way a table in a card
  does.
- The panel measures itself against the chart rather than against the window,
  which is how its right border stopped being clipped on a desktop too:
  `100vw` counts a scrollbar the layout never had, so a gutter computed from
  it is wrong by exactly that much on one platform or the other.
- **Moving a project no longer needs a drag**: Move up, Move down and Move to a
  band, from the panel header, through the same endpoint — which is also the
  first time the chart could be reordered from a keyboard.
- The 401 page carries a token field, so a hub reached from the network can be
  opened from a link that has lost its token.
- A public page under `docs/`, ready for GitHub Pages.

### Fixed

- A checkbox inside an overlay could not be ticked. The click router cancels
  the default of any click that reaches an element carrying an action, and an
  overlay carries one — its backdrop — so every click inside it was cancelled
  before the box could toggle. The default belongs to the control that was
  pressed, not to the ancestor that declares the action. This is also why
  **Content impact** in the Advanced form could never be changed.
- The Hierarchy view was unreachable while "show all dates" was the remembered
  choice: the redirect that restores it fired on every page instead of the one
  page with a scale, so the view was thrown away as it opened.

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
