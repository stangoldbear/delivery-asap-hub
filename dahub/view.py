"""
Presentation layer: HTML only.

RULE: no CSS and no JavaScript is written here. Assets live in
`static/app.css` and `static/app.js`; layout metrics are handed over as CSS
custom properties so neither side restates a number the other owns.
"""

from . import gantt, settings as settings_module
from .domain import (
    Timeline,
    format_date_long,
    group_by_tier,
    resource_row_background,
    tier_color,
    tier_row_background,
    tier_title,
)
from .markup import attrs, ensure_list, esc, safe_url, select

_LINK_FIELD_CLASS = {
    'epics': 'jira-epic-field-',
    'confluence': 'confluence-field-',
    'figma': 'figma-field-',
}


# ─── Reusable fragments ──────────────────────────────────────────────────────
def _todo_row(project_id, todo, *, done, dom_prefix):
    todo_id = todo.get('id', '')
    text = todo.get('text', '')
    deadline = todo.get('deadline', '')

    if done:
        completed = format_date_long(todo.get('completed_at', ''))
        badge = f'<span class="todo-done-at">✓ {esc(completed)}</span>' if completed else ''
    else:
        formatted = format_date_long(deadline)
        badge = f'<span class="todo-dl">\U0001F4C5 {esc(formatted)}</span>' if formatted else ''

    checked = ' checked' if done else ''
    text_class = 'todo-text done' if done else 'todo-text'
    row_class = 'todo-item-row done' if done else 'todo-item-row'
    target = attrs(project=project_id, todo=todo_id)

    return f'''<div class="{row_class}" id="{dom_prefix}-{esc(project_id)}-{esc(todo_id)}" data-text="{esc(text)}" data-dl="{esc(deadline)}">
  <input type="checkbox"{checked} data-action="todo-toggle"{target}>
  <span class="{text_class}">{esc(text)}</span>
  {badge}
  <button type="button" class="del-btn del-btn--edit" title="Edit" data-action="todo-edit"{target}>✏️</button>
  <button type="button" class="del-btn" title="Delete" data-action="todo-delete"{target}>✕</button>
</div>'''


def _todo_list(project_id, todos, *, done, dom_prefix, empty_label):
    if not todos:
        return f'<div class="todo-empty">{esc(empty_label)}</div>'
    return ''.join(_todo_row(project_id, todo, done=done, dom_prefix=dom_prefix)
                   for todo in todos)


def _link_row(project_id, kind, value, *, placeholder, href, link_class):
    field_class = _LINK_FIELD_CLASS.get(kind, f'{kind}-field-') + project_id
    target = safe_url(href)
    open_link = (f'<a href="{esc(target)}" target="_blank" rel="noopener noreferrer" '
                 f'class="{link_class}">\U0001F517 OPEN</a>') if target else ''
    return f'''<div class="link-row">
  <input type="text" class="form-input form-input--grow {field_class}" value="{esc(value)}" placeholder="{esc(placeholder)}" data-change="project-field" data-project="{esc(project_id)}">
  {open_link}
  <button type="button" class="del-btn" title="Remove" data-action="link-remove"{attrs(project=project_id, kind=kind)}>✕</button>
</div>'''


def _link_section(project_id, kind, label, values, *, placeholder, base_url='',
                  link_class='jira-link'):
    rows = ''.join(
        _link_row(
            project_id, kind, value,
            placeholder=placeholder,
            href=(base_url + str(value).strip()) if str(value).strip() else '',
            link_class=link_class,
        )
        for value in (values or [''])
    )
    return f'''<div class="field-stack">
  <div class="field-heading">
    <span>{esc(label)} ({len(values)}):</span>
    <button type="button" class="add-link-btn" data-action="link-add"{attrs(project=project_id, kind=kind)}>➕ Add</button>
  </div>
  <div id="{esc(kind)}-container-{esc(project_id)}">{rows}</div>
</div>'''


# ─── Project detail panel ────────────────────────────────────────────────────
def render_detail_row(project, tier, settings=None):
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
    history = project.get('todos_history') or []

    status_select = select(f'status-sel-{project_id}',
                           [(value, value.capitalize())
                            for value in settings_module.STATUS_OPTIONS],
                           status, project_id)
    deadline_select = select(f'deadline-type-{project_id}',
                             settings_module.DEADLINE_OPTIONS, deadline_type,
                             project_id, 'form-input form-input--narrow')

    tags = ''.join(
        f'<button type="button" class="tag-opt-btn{" active" if platform in platforms else ""}" '
        f'data-action="platform-toggle"{attrs(project=project_id, platform=platform)}>'
        f'{esc(platform)}</button>'
        for platform in config.platforms
    )

    jira_request = str(jira.get('request', '') or '')
    jira_href = safe_url(config.jira_base_url + jira_request) if jira_request else ''
    jira_open = (f'<a href="{esc(jira_href)}" target="_blank" rel="noopener noreferrer" '
                 f'class="jira-link">\U0001F517 OPEN</a>') if jira_href else ''

    epics = _link_section(project_id, 'epics', 'Epics', ensure_list(jira.get('epics')),
                          placeholder=config.jira_placeholder, base_url=config.jira_base_url)
    confluence = _link_section(project_id, 'confluence', 'Confluence',
                               ensure_list(project.get('confluence')),
                               placeholder=config.confluence_placeholder,
                               link_class='jira-link jira-link--confluence')
    figma = _link_section(project_id, 'figma', 'Figma', ensure_list(project.get('figma')),
                          placeholder=config.figma_placeholder,
                          link_class='jira-link jira-link--figma')

    blocked_display = 'block' if status == 'blocked' else 'none'
    background = resource_row_background(tier, config)
    intro_text = str(project.get('intro') or '')
    intro_display = (
        f'<span class="intro-text">{esc(intro_text)}</span>' if intro_text.strip()
        else '<span class="intro-text intro-text--empty">No general information yet. '
             'Click ✏️ to add some.</span>'
    )

    return f'''<tr class="detail-row" data-detail-tier="{esc(tier)}" data-proj-id="{esc(project_id)}" id="detail-panel-{esc(project_id)}" style="display:none">
  <td colspan="2" class="detail-cell" style="background:{background}">
    <div class="detail-panel-wrapper">
      <div class="detail-panel-box" style="background:{background}">
        <div class="detail-header">
          <h4>⚙️ Details &amp; action manager — {esc(name)}</h4>
          <button type="button" class="close-panel-btn" data-action="toggle-detail" data-project="{esc(project_id)}">Close ✕</button>
        </div>

        <div class="intro-box" id="intro-box-{esc(project_id)}" data-text="{esc(intro_text)}">
          {intro_display}
          <button type="button" class="intro-edit-btn" title="Edit intro" data-action="intro-edit" data-project="{esc(project_id)}">✏️</button>
        </div>

        <div class="detail-grid">
          <div class="detail-col">
            <div class="detail-field">
              <label>Project status</label>
              <div class="field-row">{status_select}</div>
            </div>

            <div class="detail-field" id="blocked-reason-wrap-{esc(project_id)}" style="display:{blocked_display}">
              <label class="is-danger">⚠️ Blocking reason (shown on hover)</label>
              <input type="text" id="blocked-reason-{esc(project_id)}" class="form-input" value="{esc(project.get('blocked_reason', ''))}" placeholder="e.g. waiting for UX mockups..." data-change="project-field" data-project="{esc(project_id)}">
            </div>

            <div class="detail-field">
              <label>Deadline &amp; type</label>
              <div class="field-row">
                <input type="text" id="deadline-text-{esc(project_id)}" class="form-input form-input--grow" value="{esc(deadline_raw)}" placeholder="e.g. 2026-09-27 or mid September" data-change="project-field" data-project="{esc(project_id)}">
                {deadline_select}
              </div>
            </div>

            <div class="detail-field">
              <label>Platforms / impacted teams</label>
              <div class="tags-container" id="tags-box-{esc(project_id)}">{tags}</div>
            </div>

            <div class="detail-field">
              <label>Jira</label>
              <div class="field-stack">
                <div class="field-inline">
                  <span class="field-inline__label">Request:</span>
                  <input type="text" id="jira-req-{esc(project_id)}" class="form-input form-input--grow" value="{esc(jira_request)}" placeholder="{esc(config.jira_placeholder)}" data-change="project-field" data-project="{esc(project_id)}">
                  {jira_open}
                </div>
                {epics}
              </div>
            </div>

            <div class="detail-field">
              <label>Confluence (relevant pages)</label>
              {confluence}
            </div>

            <div class="detail-field">
              <label>Figma (relevant designs)</label>
              {figma}
            </div>
          </div>

          <div class="detail-col">
            <div class="detail-field">
              <label>⚡ Project action to-do list ({len(todos)})</label>
              <div class="todos-box" id="todos-container-{esc(project_id)}">{_todo_list(project_id, todos, done=False, dom_prefix='todo-row', empty_label='No open note or action.')}</div>
              <div class="add-todo-form">
                <textarea id="new-todo-text-{esc(project_id)}" class="add-todo-form__textarea" placeholder="New note / action item..."></textarea>
                <div class="add-todo-form__row">
                  <input type="date" id="new-todo-dl-{esc(project_id)}" class="form-input form-input--date">
                  <button type="button" class="add-btn" data-action="todo-add" data-project="{esc(project_id)}">\U0001F4BE Save</button>
                  <button type="button" class="cancel-btn" data-action="todo-add-cancel" data-project="{esc(project_id)}">Cancel</button>
                </div>
              </div>
            </div>

            <div class="detail-field">
              <button type="button" class="toggle-hist-btn" id="btn-hist-{esc(project_id)}" data-action="toggle-history" data-project="{esc(project_id)}">\U0001F4DC Completed actions ({len(history)}) ▼</button>
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
    config = settings or settings_module.current()
    grouped = group_by_tier(projects, config)
    blocks, total_active, total_done = [], 0, 0

    for tier in config.project_tiers:
        cards = []
        for project in grouped.get(tier, []):
            todos = project.get('todos') or []
            history = project.get('todos_history') or []
            total_active += len(todos)
            total_done += len(history)
            if todos or history:
                cards.append(_todo_card(project, tier, todos, history, config))

        if cards:
            blocks.append(
                f'<div class="tier-group">'
                f'<h4 style="color:{tier_color(tier, config)}">{esc(tier_title(tier, config))}</h4>'
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
        sections += ('<div class="todo-group-label todo-group-label--active">'
                     '⚡ OPEN ACTIONS:</div>')
        sections += _todo_list(project_id, todos, done=False,
                               dom_prefix='global-todo-row', empty_label='')

    if history:
        sections += ('<div class="todo-group-label todo-group-label--history">'
                     '\U0001F4DC COMPLETED:</div>')
        sections += _todo_list(project_id, history, done=True,
                               dom_prefix='global-todo-row', empty_label='')

    return f'''<div class="global-todo-card" style="border-left:4px solid {tier_color(tier, config)};background:{tier_row_background(tier, config)}">
  <div class="global-todo-card__head">
    <strong class="global-todo-card__title">{esc(name)} ({esc(project_id)})</strong>
    <button type="button" class="action-btn" data-action="toggle-detail" data-project="{esc(project_id)}">⚙️ Info &amp; actions</button>
  </div>
  {sections}
</div>'''


# ─── Full document ───────────────────────────────────────────────────────────
def _css_variables(timeline, settings):
    variables = dict(settings.css_variables())
    variables['--timeline-w'] = f'{timeline.width}px'
    body = ''.join(f'{name}:{value};' for name, value in variables.items())
    return f'<style>:root{{{body}}}</style>'


def render_page(projects, tasks, *, hide_past=False, today=None, settings=None):
    config = settings or settings_module.current()
    timeline = Timeline(tasks, settings=config, hide_past=hide_past, today=today)
    chart = gantt.render(projects, tasks, timeline,
                         detail_row=lambda project, tier: render_detail_row(project, tier, config),
                         settings=config)
    todos_html, active_count, done_count = render_global_todos(projects, config)
    toggle_label = 'Show all dates' if hide_past else 'Show from today'
    toggle_target = '0' if hide_past else '1'
    toggle_icon = '\U0001F4C5' if hide_past else '\U0001F4C6'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(config.title)}</title>
  <link rel="stylesheet" href="/static/app.css">
  {_css_variables(timeline, config)}
</head>
<body>
<div class="container">
  <header>
    <div>
      <h1>{esc(config.title)}</h1>
      <div class="meta">{esc(config.subtitle)}</div>
    </div>
    <div class="header-side">
      <strong>DM:</strong> {esc(config.owner)}<br>
      <strong>Active projects:</strong> {len(projects)}
    </div>
  </header>

  <div class="global-todos-box">
    <div class="global-todos-header" data-action="toggle-global">
      <div class="global-todos-title">
        <span>⚡ Aggregated action items &amp; project notes</span>
        <span class="counter-pill">{active_count} open / {done_count} done</span>
      </div>
      <button type="button" id="btn-toggle-global-todos" class="tier-toggle-btn" data-action="toggle-global">▼</button>
    </div>
    <div id="global-todos-content" class="global-todos-content">{todos_html}</div>
  </div>

  <div class="gantt-box">
    <div class="gantt-toolbar">
      <div class="gantt-toolbar__hint">
        \U0001F3AF Hierarchy: <strong>TIER → PROJECT (priority) → PEOPLE &amp; SUB-TASKS</strong>
      </div>
      <div class="gantt-toolbar__actions">
        <button type="button" class="action-btn action-btn--slate" data-action="expand-tiers">Expand all tiers</button>
        <button type="button" class="action-btn action-btn--steel" data-action="collapse-tiers">Collapse all tiers</button>
        <button type="button" class="action-btn action-btn--graphite" data-action="expand-projects">Expand all projects</button>
        <button type="button" class="action-btn action-btn--charcoal" data-action="collapse-projects">Collapse all projects</button>
        <button type="button" class="action-btn action-btn--today" data-action="toggle-hide-past" data-target="{toggle_target}">{toggle_icon} {toggle_label}</button>
      </div>
    </div>
    {chart}
  </div>

  <footer>{esc(config.footer)}</footer>
</div>
<div id="toast-host"></div>
<div id="advanced-edit-overlay" class="advedit-overlay" style="display:none" data-action="advanced-edit-backdrop">
  <div class="advedit-panel">
    <div class="advedit-header">
      <h3 id="advedit-title">\U0001F6E0️ Advanced edit</h3>
      <button type="button" class="close-panel-btn" data-action="advanced-edit-close">Close ✕</button>
    </div>
    <div class="advedit-tabs">
      <button type="button" class="advedit-tab advedit-tab--active" id="advedit-tab-form" data-action="advanced-edit-tab" data-tab="form">\U0001F4CB Form</button>
      <button type="button" class="advedit-tab" id="advedit-tab-raw" data-action="advanced-edit-tab" data-tab="raw">\U0001F4DD RAW</button>
    </div>
    <div id="advedit-body-form" class="advedit-body">Loading...</div>
    <div id="advedit-body-raw" class="advedit-body" style="display:none">
      <textarea id="advedit-raw-textarea" class="advedit-raw-textarea" spellcheck="false"></textarea>
    </div>
    <div class="advedit-footer">
      <button type="button" class="add-btn" id="advedit-save-form" data-action="advanced-edit-save-form">\U0001F4BE Save form</button>
      <button type="button" class="add-btn" id="advedit-save-raw" style="display:none" data-action="advanced-edit-save-raw">\U0001F4BE Save RAW</button>
      <button type="button" class="cancel-btn" data-action="advanced-edit-close">Cancel</button>
    </div>
  </div>
</div>
<script src="/static/app.js"></script>
</body>
</html>'''
