"""
Presentation layer: HTML only.

RULE: no CSS and no JavaScript is written here. Assets live in
`static/app.css` and `static/app.js`; layout metrics are handed over as CSS
custom properties so neither side restates a number the other owns.
"""

import json
from urllib.parse import quote

from . import gantt, settings as settings_module
from .domain import (
    Timeline,
    chart_spans,
    project_milestones,
    format_date_long,
    group_by_display,
    group_color,
    group_order,
    group_title,
    project_span,
    project_tasks,
    tier_color,
)
from .gantt import CARET_OPEN
from .markup import (
    attrs, ensure_list, esc, human_size, icon, render_markdown, safe_url, select,
)

_LINK_FIELD_CLASS = {
    'epics': 'jira-epic-field-',
    'confluence': 'confluence-field-',
    'figma': 'figma-field-',
}

# One motif, used three times: the milestone marker on the timeline, the
# wordmark, and the favicon below.
_FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'"
            "%3E%3Cpath fill='%23475569' d='M8 1.2 14.8 8 8 14.8 1.2 8Z'/%3E%3C/svg%3E")


# ─── Reusable fragments ──────────────────────────────────────────────────────
def _editable_field(label, view, form, *, wrap_id='', style=''):
    """
    A value that reads as information and becomes a form on double click.

    Both halves are rendered here, and the browser only flips which one is
    hidden: an editor whose markup lives in JavaScript is a second source of
    truth for the same field.
    """
    identifier = f' id="{esc(wrap_id)}"' if wrap_id else ''
    inline_style = f' style="{style}"' if style else ''
    return f'''<div class="detail-field editable-field"{identifier}{inline_style}>
  <span class="field-label">{label}</span>
  <div class="editable-view" tabindex="0" title="Double-click to edit">{view}</div>
  <div class="editable-form" hidden>
    {form}
    <div class="editable-actions">
      <button type="button" class="btn btn--default btn--sm" data-action="field-save">Save</button>
      <button type="button" class="btn btn--secondary btn--sm" data-action="field-cancel">Cancel</button>
    </div>
  </div>
</div>'''


def _link_chip(value, base_url, link_class):
    text = str(value).strip()
    if not text:
        return ''
    href = safe_url(base_url + text)
    if not href:
        return f'<span class="badge badge--outline">{esc(text)}</span>'
    return (f'<a class="{link_class}" href="{esc(href)}" target="_blank" '
            f'rel="noopener noreferrer">{icon("link")}{esc(text)}</a>')

def _todo_row(project_id, todo, *, done, dom_prefix):
    todo_id = todo.get('id', '')
    text = todo.get('text', '')
    deadline = todo.get('deadline', '')

    if done:
        completed = format_date_long(todo.get('completed_at', ''))
        badge = f'<span class="todo-done-at">{esc(completed)}</span>' if completed else ''
    else:
        formatted = format_date_long(deadline)
        badge = f'<span class="todo-dl">{esc(formatted)}</span>' if formatted else ''

    checked = ' checked' if done else ''
    text_class = 'todo-text done' if done else 'todo-text'
    row_class = 'todo-item-row done' if done else 'todo-item-row'
    target = attrs(project=project_id, todo=todo_id)

    draggable = '' if done else ' draggable="true"'
    return f'''<div class="{row_class}" id="{dom_prefix}-{esc(project_id)}-{esc(todo_id)}" data-text="{esc(text)}" data-dl="{esc(deadline)}"{target}{draggable}>
  <input type="checkbox"{checked} data-action="todo-toggle"{target}>
  <span class="{text_class}" title="Double-click to edit">{render_markdown(text)}</span>
  {badge}
  <button type="button" class="btn btn--ghost btn--sm btn--icon btn--danger" title="Delete" aria-label="Delete this note" data-action="todo-delete"{target}>✕</button>
</div>'''


def _todo_list(project_id, todos, *, done, dom_prefix, empty_label):
    if not todos:
        return f'<div class="todo-empty">{esc(empty_label)}</div>'
    return ''.join(_todo_row(project_id, todo, done=done, dom_prefix=dom_prefix)
                   for todo in todos)


def _link_row(project_id, kind, value, *, placeholder, param):
    field_class = _LINK_FIELD_CLASS.get(kind, f'{kind}-field-') + project_id
    return f'''<div class="link-row">
  <input type="text" class="form-input form-input--grow {field_class}" value="{esc(value)}" placeholder="{esc(placeholder)}" data-param="{esc(param)}" data-kind="list">
  <button type="button" class="btn btn--ghost btn--sm btn--icon btn--danger" title="Remove" aria-label="Remove this link" data-action="link-remove"{attrs(project=project_id, kind=kind)}>✕</button>
</div>'''


def _link_section(project_id, kind, label, values, *, param, placeholder, base_url='',
                  link_class='jira-link'):
    chips = ''.join(_link_chip(value, base_url, link_class) for value in values)
    rows = ''.join(
        _link_row(project_id, kind, value, placeholder=placeholder, param=param)
        for value in (values or [''])
    )
    view = (f'<div class="chips" data-list="{esc(param)}" data-base-url="{esc(base_url)}" '
            f'data-link-class="{esc(link_class)}">{chips}</div>' if chips
            else f'<div class="chips" data-list="{esc(param)}" data-base-url="{esc(base_url)}" '
                 f'data-link-class="{esc(link_class)}">'
                 f'<span class="editable-empty">None</span></div>')
    form = f'''<div id="{esc(kind)}-container-{esc(project_id)}">{rows}</div>
    <div><button type="button" class="btn btn--outline btn--sm" data-action="link-add"{attrs(project=project_id, kind=kind)}>{icon('plus')}Add</button></div>'''
    return _editable_field(f'{esc(label)} (<span data-count="{esc(param)}">{len(values)}</span>)',
                           view, form)


def _attachment_rows(project_id, attachments):
    if not attachments:
        rows = '<div class="todo-empty">No file attached.</div>'
    else:
        rows = ''.join(
            f'<div class="attachment-row">'
            f'<a class="attachment-row__name" href="/api/project/{esc(quote(project_id))}/attachments/{esc(quote(entry["name"]))}" '
            f'target="_blank" rel="noopener noreferrer" title="{esc(entry["name"])}">'
            f'{icon("clip")}{esc(entry["name"])}</a>'
            f'<span class="attachment-row__size">{esc(human_size(entry["size"]))}</span>'
            f'<button type="button" class="btn btn--ghost btn--sm btn--icon btn--danger" title="Remove" '
            f'aria-label="Remove this attachment" data-action="attachment-delete"'
            f'{attrs(project=project_id, name=entry["name"])}>✕</button>'
            f'</div>'
            for entry in attachments
        )
    return f'''<div class="field-stack">
  <div id="attachments-{esc(project_id)}">{rows}</div>
  <label class="attachment-upload">
    <input type="file" multiple data-change="attachment-upload" data-project="{esc(project_id)}">
  </label>
</div>'''


# ─── Project detail panel ────────────────────────────────────────────────────
def render_detail_row(project, group, settings=None):
    config = settings or settings_module.current()
    project_id = project['id']
    name = project.get('name', project_id)
    status = str(project.get('status', 'active')).lower()
    dates = project.get('dates') or {}
    footprint = project.get('tech_footprint') or {}
    jira = project.get('jira') or {}

    deadline_raw = dates.get('deadline_text') or dates.get('target_delivery') or 'N/A'
    deadline_type = str(dates.get('deadline_type', 'soft')).lower()
    platforms = ensure_list(footprint.get('platforms'))
    todos = project.get('todos') or []
    history = project.get('done') or []
    attachments = project.get('_attachments') or []

    status_select = select(f'status-sel-{project_id}',
                           [(value, value.capitalize())
                            for value in settings_module.STATUS_OPTIONS],
                           status, 'status')
    deadline_select = select(f'deadline-type-{project_id}',
                             settings_module.DEADLINE_OPTIONS, deadline_type,
                             'deadline_type', 'form-input form-input--narrow')
    status_style = settings_module.STATUS_STYLES.get(status, settings_module.STATUS_FALLBACK)
    deadline_style = settings_module.DEADLINE_STYLES.get(
        deadline_type, settings_module.DEADLINE_STYLES['soft'])

    tags = ''.join(
        f'<button type="button" class="tag-opt-btn{" active" if platform in platforms else ""}" '
        f'aria-pressed="{"true" if platform in platforms else "false"}" '
        f'data-action="platform-toggle"{attrs(project=project_id, platform=platform)}>'
        f'{esc(platform)}</button>'
        for platform in config.platforms
    )

    jira_request = str(jira.get('request', '') or '')
    jira_href = safe_url(config.jira_base_url + jira_request) if jira_request else ''
    jira_open = (f'<a href="{esc(jira_href)}" target="_blank" rel="noopener noreferrer" '
                 f'class="jira-link">{icon("link")}Open</a>') if jira_href else ''

    epics = _link_section(project_id, 'epics', 'Epics', ensure_list(jira.get('epics')),
                          param='jira_epics', placeholder=config.jira_placeholder,
                          base_url=config.jira_base_url)
    confluence = _link_section(project_id, 'confluence', 'Confluence',
                               ensure_list(project.get('confluence')),
                               param='confluence_links',
                               placeholder=config.confluence_placeholder)
    figma = _link_section(project_id, 'figma', 'Figma', ensure_list(project.get('figma')),
                          param='figma_links', placeholder=config.figma_placeholder)

    milestones = project_milestones(project, config)
    milestone_chips = ''.join(
        f'<button type="button" class="badge badge--outline" data-action="milestone-open"'
        f'{attrs(project=project_id, milestone=mark["id"], text=mark["text"])}'
        f' data-date="{mark["date"].strftime("%Y-%m-%d")}">{icon("diamond")}'
        f'{esc(format_date_long(mark["date"], config))}'
        f'{" — " + esc(mark["text"]) if mark["text"] else ""}</button>'
        for mark in milestones
    ) or '<span class="editable-empty">None</span>'

    blocked_display = 'block' if status == 'blocked' else 'none'
    intro_text = str(project.get('intro') or '')
    intro_display = (
        f'<span class="intro-text" title="Double-click to edit">'
        f'{render_markdown(intro_text)}</span>'
        if intro_text.strip()
        else '<span class="intro-text intro-text--empty" title="Double-click to edit">'
             'No general information yet. Double-click to add some.</span>'
    )

    return f'''<tr class="detail-row" data-detail-group="{esc(group)}" data-proj-id="{esc(project_id)}" id="detail-panel-{esc(project_id)}" style="display:none">
  <td colspan="2" class="detail-cell">
    <div class="detail-panel-wrapper">
      <div class="detail-panel-box">
        <div class="detail-header">
          <h4>Notes &amp; actions — {esc(name)}</h4>
          <button type="button" class="btn btn--secondary btn--sm" data-action="toggle-detail" data-project="{esc(project_id)}">Close</button>
        </div>

        <div class="intro-box" id="intro-box-{esc(project_id)}" data-project="{esc(project_id)}" data-text="{esc(intro_text)}">
          {intro_display}
        </div>

        <div class="detail-grid">
          <div class="detail-col">
            {_editable_field(
                'Project name',
                f'<span data-from="name" data-empty="Untitled">{esc(name)}</span>',
                f'<input type="text" class="form-input" value="{esc(name)}" '
                f'data-param="name" data-value="{esc(name)}" '
                f'aria-label="Project name">')}

            {_editable_field(
                'Project status',
                f'<span class="status-pill" data-from="status" data-format="status" '
                f'style="background:{status_style["bg"]};color:{status_style["fg"]}">'
                f'{esc(status.upper())}</span>',
                f'<div class="field-row">{status_select}</div>')}

            {_editable_field(
                'Blocking reason (shown on hover)',
                f'<span data-from="blocked_reason" data-empty="Not set">'
                f'{esc(project.get("blocked_reason", "")) or "Not set"}</span>',
                f'<input type="text" id="blocked-reason-{esc(project_id)}" class="form-input" '
                f'value="{esc(project.get("blocked_reason", ""))}" data-param="blocked_reason" '
                f'data-value="{esc(project.get("blocked_reason", ""))}" '
                f'placeholder="e.g. waiting for UX mockups...">',
                wrap_id=f'blocked-reason-wrap-{project_id}',
                style=f'display:{blocked_display}')}

            {_editable_field(
                'Deadline &amp; type',
                f'<span data-from="deadline_text" data-format="date">'
                f'{esc(format_date_long(deadline_raw, config))}</span> '
                f'<span class="deadline-pill" data-from="deadline_type" data-format="deadline" '
                f'style="background:{deadline_style["bg"]};color:{deadline_style["fg"]}">'
                f'{esc(deadline_type.upper())}</span>',
                f'<div class="field-row">'
                f'<input type="text" id="deadline-text-{esc(project_id)}" '
                f'class="form-input form-input--grow" value="{esc(deadline_raw)}" '
                f'data-param="deadline_text" data-value="{esc(deadline_raw)}" '
                f'placeholder="e.g. 2026-09-27 or mid September">{deadline_select}</div>')}

            <div class="detail-field">
              <label>Platforms / impacted teams</label>
              <div class="tags-container" id="tags-box-{esc(project_id)}">{tags}</div>
            </div>

            {_editable_field(
                'Jira request',
                f'<span data-from="jira_request" data-empty="Not set" '
                f'data-link-base="{esc(config.jira_base_url)}">'
                f'{esc(jira_request) or "Not set"}</span> {jira_open}',
                f'<input type="text" id="jira-req-{esc(project_id)}" '
                f'class="form-input form-input--grow" value="{esc(jira_request)}" '
                f'data-param="jira_request" data-value="{esc(jira_request)}" '
                f'placeholder="{esc(config.jira_placeholder)}">')}

            {epics}

            {confluence}

            {figma}

            <div class="detail-field">
              <div class="field-heading">
                <span class="field-label">Milestones ({len(milestones)})</span>
                <button type="button" class="btn btn--outline btn--sm" data-action="milestone-open" data-project="{esc(project_id)}">{icon('plus')}Add</button>
              </div>
              <div class="chips" id="milestones-{esc(project_id)}">{milestone_chips}</div>
            </div>

            <div class="detail-field">
              <label>Attachments ({len(attachments)})</label>
              {_attachment_rows(project_id, attachments)}
            </div>
          </div>

          <div class="detail-col">
            <div class="detail-field">
              <label for="new-todo-text-{esc(project_id)}">Project action to-do list (<span id="todos-count-{esc(project_id)}">{len(todos)}</span>)</label>
              <div class="todos-box" id="todos-container-{esc(project_id)}">{_todo_list(project_id, todos, done=False, dom_prefix='todo-row', empty_label='No open note or action.')}</div>
              <div class="add-todo-form">
                <textarea id="new-todo-text-{esc(project_id)}" class="add-todo-form__textarea" placeholder="New note / action item..."></textarea>
                <div class="add-todo-form__row">
                  <input type="date" id="new-todo-dl-{esc(project_id)}" class="form-input form-input--date" aria-label="Due date">
                  <button type="button" class="btn btn--default btn--sm" data-action="todo-add" data-project="{esc(project_id)}">Save</button>
                  <button type="button" class="btn btn--secondary btn--sm" data-action="todo-add-cancel" data-project="{esc(project_id)}">Cancel</button>
                </div>
              </div>
            </div>

            <div class="detail-field">
              <button type="button" class="btn btn--outline btn--sm btn--wide" id="btn-hist-{esc(project_id)}" data-action="toggle-history" data-project="{esc(project_id)}">Completed actions ({len(history)}) {CARET_OPEN}</button>
              <div class="history-box" id="history-box-{esc(project_id)}" data-proj-id="{esc(project_id)}" style="display:none">{_todo_list(project_id, history, done=True, dom_prefix='todo-row', empty_label='Nothing in the history yet.')}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </td>
</tr>'''


# ─── Aggregated to-do view ───────────────────────────────────────────────────
def render_global_todos(projects, settings=None):
    """
    Open actions, by tier.

    Finished and abandoned work is left out: it should not keep asking for
    attention. Its notes stay readable in its own panel.
    """
    config = settings or settings_module.current()
    grouped = group_by_display(projects, config)
    blocks, total_active, total_done = [], 0, 0

    for tier in config.tiers:
        cards = []
        for project in grouped.get(tier, []):
            todos = project.get('todos') or []
            history = project.get('done') or []
            total_active += len(todos)
            total_done += len(history)
            if todos or history:
                cards.append(_todo_card(project, tier, todos, history, config))

        if cards:
            blocks.append(
                f'<div class="tier-group">'
                f'<h4><span class="tier-group__marker" style="background:{tier_color(tier, config)}">'
                f'</span>{esc(group_title(tier, config))}</h4>'
                f'{"".join(cards)}</div>'
            )

    if not blocks:
        return ('<div class="todo-empty">No note or action found in the vault.</div>',
                total_active, total_done)

    return ''.join(blocks), total_active, total_done


def _todo_card(project, tier, todos, history, config):
    project_id = project['id']
    name = project.get('name', project_id)
    sections = ''

    if todos:
        sections += ('<div class="todo-group" data-group="open">'
                     '<div class="todo-group-label">Open actions</div>'
                     + _todo_list(project_id, todos, done=False,
                                  dom_prefix='global-todo-row', empty_label='')
                     + '</div>')

    if history:
        sections += ('<div class="todo-group" data-group="done">'
                     '<div class="todo-group-label todo-group-label--history">Completed</div>'
                     + _todo_list(project_id, history, done=True,
                                  dom_prefix='global-todo-row', empty_label='')
                     + '</div>')

    return f'''<div class="global-todo-card" style="border-left:3px solid {tier_color(tier, config)}">
  <div class="global-todo-card__head" data-card="{esc(project_id)}">
    <strong class="global-todo-card__title" title="{esc(project_id)}">{esc(name)}</strong>
    <button type="button" class="btn btn--ghost btn--sm" data-action="toggle-detail" data-project="{esc(project_id)}">{icon('panel')}Notes &amp; actions</button>
  </div>
  {sections}
</div>'''


# ─── Full document ───────────────────────────────────────────────────────────
def _css_variables(timeline, settings):
    """
    Layout metrics for the stylesheet and the script.

    Emitted before app.css on purpose: these are the defaults, and a media
    query in the stylesheet may narrow them for a small screen. Python owns
    the numbers, CSS owns the responsive policy.
    """
    variables = dict(settings.css_variables())
    if timeline is not None:
        variables['--timeline-w'] = f'{timeline.width}px'
    body = ''.join(f'{name}:{value};' for name, value in variables.items())
    return f'<style>:root{{{body}}}</style>'


def _shell(config, *, timeline, header_side, content, overlays=''):
    """The page around the content: head, header, footer, toasts."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(config.title)}</title>
  <link rel="icon" href="{_FAVICON}">
  {_css_variables(timeline, config)}
  <link rel="stylesheet" href="/static/app.css">
</head>
<body>
<div class="container" data-months="{esc(",".join(config.months))}" data-status-styles="{esc(json.dumps(settings_module.STATUS_STYLES))}" data-deadline-styles="{esc(json.dumps(settings_module.DEADLINE_STYLES))}">
  <header>
    <div class="wordmark">
      {icon('diamond')}
      <h1>{esc(config.title)}</h1>
    </div>
    {header_side}
  </header>

  {content}

  <footer>
    <div class="footer-prefs">
      <label class="footer-pref"><input type="checkbox" data-change="preference" data-pref="save"> Ask before saving</label>
      <label class="footer-pref"><input type="checkbox" data-change="preference" data-pref="cancel"> Ask before discarding</label>
    </div>
    <div class="footer-line">{esc(config.footer)}</div>
  </footer>
</div>
<div id="toast-host"></div>
{overlays}
<script src="/static/app.js"></script>
</body>
</html>'''


def _nav(active, count):
    """Two views over the same vault; the count belongs to both."""
    links = ''.join(
        f'<a class="btn btn--sm {"btn--secondary" if key == active else "btn--ghost"}" '
        f'href="{href}">{esc(label)}</a>'
        for key, href, label in (('chart', '/', 'Chart'), ('hierarchy', '/hierarchy', 'Hierarchy'))
    )
    return (f'<div class="header-side">{links}'
            f'<span class="header-stat"><strong>{count}</strong> projects</span></div>')


def render_page(projects, *, hide_past=False, today=None, settings=None):
    config = settings or settings_module.current()
    timeline = Timeline(chart_spans(projects, config), settings=config,
                        hide_past=hide_past, today=today)
    chart = gantt.render(projects, timeline,
                         detail_row=lambda project, group: render_detail_row(project, group, config),
                         settings=config)
    todos_html, active_count, done_count = render_global_todos(projects, config)
    toggle_label = 'Show all dates' if hide_past else 'Show from today'
    toggle_target = '0' if hide_past else '1'

    content = f"""<div class="global-todos-box">
    <div class="global-todos-header" data-action="toggle-global">
      <div class="global-todos-title">
        <span>Actions &amp; notes</span>
        <span class="badge" id="global-todos-counter" data-open="{active_count}" data-done="{done_count}">{active_count} open / {done_count} done</span>
      </div>
      <button type="button" id="btn-toggle-global-todos" class="btn btn--ghost btn--sm btn--icon" data-action="toggle-global" aria-label="Collapse or expand the aggregated actions">{CARET_OPEN}</button>
    </div>
    <div id="global-todos-content" class="global-todos-content">{todos_html}</div>
  </div>

  <div class="gantt-box">
    <div class="gantt-toolbar">
      <div class="gantt-search">
        <input type="search" id="search-field" class="form-input" placeholder="Search projects, people, notes" aria-label="Search the chart" data-change="search">
        <span class="gantt-search__count" id="search-count"></span>
      </div>
      <div class="gantt-toolbar__actions">
        <button type="button" class="btn btn--secondary btn--sm" data-action="expand-groups">Expand groups</button>
        <button type="button" class="btn btn--secondary btn--sm" data-action="collapse-groups">Collapse groups</button>
        <button type="button" class="btn btn--secondary btn--sm" data-action="expand-projects">Expand projects</button>
        <button type="button" class="btn btn--secondary btn--sm" data-action="collapse-projects">Collapse projects</button>
        <button type="button" class="btn btn--outline btn--sm" data-action="toggle-hide-past" data-target="{toggle_target}">{icon('calendar')}{toggle_label}</button>
      </div>
    </div>
    {chart}
  </div>"""

    overlay = f"""<div id="advanced-edit-overlay" class="advedit-overlay" style="display:none" data-action="advanced-edit-backdrop" role="dialog" aria-modal="true" aria-labelledby="advedit-title">
  <div class="advedit-panel">
    <div class="advedit-header">
      <h3 id="advedit-title">Advanced edit</h3>
      <button type="button" class="btn btn--secondary btn--sm" data-action="advanced-edit-close">Close</button>
    </div>
    <div class="tabs advedit-tabs">
      <button type="button" class="tab tab--active" id="advedit-tab-form" data-action="advanced-edit-tab" data-tab="form">Form</button>
      <button type="button" class="tab" id="advedit-tab-raw" data-action="advanced-edit-tab" data-tab="raw">Markdown</button>
    </div>
    <div id="advedit-body-form" class="advedit-body">Loading...</div>
    <div id="advedit-body-raw" class="advedit-body" style="display:none">
      <textarea id="advedit-raw-textarea" class="advedit-raw-textarea" spellcheck="false" aria-label="The card as markdown"></textarea>
    </div>
    <div class="advedit-footer">
      <button type="button" class="btn btn--secondary btn--sm" data-action="advanced-edit-close">Cancel</button>
      <button type="button" class="btn btn--default btn--sm" id="advedit-save-form" data-action="advanced-edit-save-form">Save</button>
      <button type="button" class="btn btn--default btn--sm" id="advedit-save-raw" style="display:none" data-action="advanced-edit-save-raw">Save</button>
    </div>
  </div>
</div>"""

    return _shell(config, timeline=timeline, header_side=_nav('chart', len(projects)),
                  content=content, overlays=overlay)


# ─── Hierarchy: the whole vault as a tree, and as one document ───────────────
def _tree(projects, settings):
    """The hierarchy as a list: group → project → the rows it declares."""
    grouped = group_by_display(projects, settings)
    blocks = []

    for tier in group_order(settings):
        tier_projects = grouped.get(tier, [])
        if not tier_projects:
            continue

        items = []
        for project in tier_projects:
            rows = project_tasks(project, settings)
            span = project_span(project, settings)
            when = (f'{format_date_long(span[0], settings)} → '
                    f'{format_date_long(span[1], settings)}') if span else 'no span declared'
            status = str(project.get('status', 'active')).lower()
            style = settings_module.STATUS_STYLES.get(status, settings_module.STATUS_FALLBACK)

            people = ''.join(
                f'<li class="tree__row">'
                f'<span class="resource-line__role" style="color:{row["color"]}">{esc(row["role"])}:</span> '
                f'{esc(row["who"])} <span class="tree__when">'
                f'{esc(format_date_long(row["start"], settings))} → '
                f'{esc(format_date_long(row["end"], settings))}</span>'
                f'{" — " + esc(row["note"]) if row["note"] else ""}</li>'
                for row in rows
            )

            items.append(
                f'<li class="tree__project">'
                f'<span class="prio-badge">{esc(project.get("priority", ""))}</span> '
                f'<strong>{esc(project.get("name", project["id"]))}</strong> '
                f'<span class="status-pill" style="background:{style["bg"]};color:{style["fg"]}">'
                f'{esc(status.upper())}</span> '
                f'<span class="tree__when">{esc(when)}</span>'
                f'{f"<ul>{people}</ul>" if people else ""}</li>')

        blocks.append(
            f'<li class="tree__tier">'
            f'<span class="tier-row__marker" style="background:{group_color(tier, settings)}"></span>'
            f'{esc(group_title(tier, settings))} <span class="badge">{len(tier_projects)}</span>'
            f'<ul>{"".join(items)}</ul></li>')

    return f'<ul class="tree">{"".join(blocks)}</ul>' if blocks else (
        '<div class="todo-empty">No project card in the vault.</div>')


def render_hierarchy_page(projects, markdown, *, settings=None):
    """
    Two readings of the same vault: the structure, and the text behind it.

    The markdown tab is every card in one editable document — the monthly
    snapshot, and the way to edit many cards at once.
    """
    config = settings or settings_module.current()

    content = f"""<div class="gantt-box">
    <div class="tabs">
      <button type="button" class="tab tab--active" data-action="view-tab" data-tab="structure">Structure</button>
      <button type="button" class="tab" data-action="view-tab" data-tab="markdown">Markdown</button>
    </div>

    <div id="view-structure" class="view-panel">{_tree(projects, config)}</div>

    <div id="view-markdown" class="view-panel" hidden>
      <p class="view-hint">Every card, in the order the chart draws them. A block
      with an unknown <code>- id:</code> creates a card; a card whose block is not
      here is left alone — nothing is ever deleted from this screen.</p>
      <textarea id="vault-markdown" class="advedit-raw-textarea" spellcheck="false" aria-label="Every card as one markdown document">{esc(markdown)}</textarea>
      <div class="view-actions">
        <button type="button" class="btn btn--default btn--sm" data-action="vault-markdown-save">Save all</button>
        <a class="btn btn--outline btn--sm" href="/api/vault/markdown" download>{icon('clip')}Download snapshot</a>
      </div>
    </div>
  </div>"""

    return _shell(config, timeline=None, header_side=_nav('hierarchy', len(projects)),
                  content=content)
