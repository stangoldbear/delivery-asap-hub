"""
Gantt chart rendering: header, tier rows, project rows, resource rows.

Geometry and colours come from `domain`; layout metrics travel as CSS custom
properties, so the stylesheet and the resize script never restate them.
"""

from . import settings as settings_module
from .domain import (
    format_date_long,
    group_by_tier,
    member_name,
    resolve_role,
    resource_row_background,
    role_color,
    summary_bar_color,
    tier_color,
    tier_row_background,
    tier_title,
)
from .markup import ensure_list, esc


def render(projects, tasks, timeline, *, detail_row, settings=None):
    """
    The whole chart as one `<table>`.

    `detail_row(project, tier)` is injected: the chart places the expandable
    panel row but knows nothing about its contents.
    """
    config = settings or settings_module.current()
    grouped = group_by_tier(projects, config)
    orphan_tasks = [task for task in tasks if not task['project_id']]

    parts = [_header(timeline, config)]

    for tier in config.tiers:
        tier_projects = grouped.get(tier, [])
        is_other = tier == config.other_tier
        if is_other and not orphan_tasks:
            continue
        if not is_other and not tier_projects:
            continue

        count = len(orphan_tasks) if is_other else len(tier_projects)
        parts.append(_tier_header(tier, count, config))

        for position, project in enumerate(tier_projects, start=1):
            parts.extend(_project_block(project, tier, tasks, timeline, position,
                                        detail_row, config))

        if is_other:
            parts.extend(_orphan_row(task, timeline, config) for task in orphan_tasks)

    parts.append('</tbody></table></div>')
    return '\n'.join(parts)


def _header(timeline, config):
    months = ''.join(
        f'<div class="month-cell" style="width:calc(var(--col-w) * {count})">'
        f'{config.month_abbr[month - 1]} {year}</div>'
        for (year, month), count in timeline.months
    )
    days = ''.join(
        f'<div class="day-cell day-cell--{timeline.day_state(day)}">{day.day}</div>'
        for day in timeline.days
    )

    today_index = timeline.today_index
    band = ''
    if today_index is not None:
        offset = today_index * timeline.col_width
        band = (f'<div class="today-band" data-offset="{offset}" '
                f'style="--today-offset:{offset}px"></div>')

    return f'''<div class="gantt-scroll" id="gantt-scroll">
{band}
<div class="col-resize-handle" id="col-resize-handle"><div class="col-resize-handle__bar" title="Drag to resize"></div></div>
<table class="gantt-table" id="gantt-table">
  <colgroup>
    <col class="label-col">
    <col class="timeline-col">
  </colgroup>
  <thead>
    <tr>
      <th class="label-head sticky-col">
        <div class="label-head__title">PROJECT &amp; ASSIGNED RESOURCES</div>
      </th>
      <th class="timeline-head">
        <div class="timeline-strip">{months}</div>
      </th>
    </tr>
    <tr>
      <th class="label-head sticky-col">
        <div class="label-head__sub">Filter / expand the hierarchy</div>
      </th>
      <th class="timeline-head">
        <div class="timeline-strip">{days}</div>
      </th>
    </tr>
  </thead>
  <tbody>'''


def _tier_header(tier, count, config):
    color = tier_color(tier, config)
    return f'''<tr class="tier-row" data-tier="{esc(tier)}" style="border-top:2px solid {color}">
  <td colspan="2" class="tier-row__cell">
    <div class="tier-row__inner" style="border-left:5px solid {color}">
      <button type="button" class="tier-toggle-btn" id="btn-tier-{esc(tier)}" data-action="toggle-tier" data-tier="{esc(tier)}">▼</button>
      <span>{esc(tier_title(tier, config))}</span>
      <span class="tier-row__count" style="background:{color}">{count}</span>
    </div>
  </td>
</tr>'''


def _project_block(project, tier, tasks, timeline, position, detail_row, config):
    project_id = project['id']
    project_tasks = [task for task in tasks if task['project_id'] == project_id]

    rows = [_project_row(project, tier, project_tasks, timeline, position, config)]
    rows.extend(_resource_row(project_id, tier, task, timeline, config)
                for task in project_tasks)
    rows.append(detail_row(project, tier))
    return rows


def _summary_bar(project_tasks, timeline, tier, status, config):
    if not project_tasks:
        return ''
    start = min(task['start'] for task in project_tasks)
    end = max(task['end'] for task in project_tasks)
    geometry = timeline.geometry(start, end)
    if not geometry:
        return ''
    left, width = geometry
    fill = summary_bar_color(tier, status, config)
    span = (f'{format_date_long(start, config)} → {format_date_long(end, config)}')
    return (f'<div class="task-bar summary-bar" style="left:{left}px;width:{width}px;'
            f'background:{fill};border:1px dashed {fill}" '
            f'title="Project span: {esc(span)}"></div>')


def _project_row(project, tier, project_tasks, timeline, position, config):
    project_id = project['id']
    name = project.get('name', project_id)
    status = str(project.get('status', 'active')).lower()
    dates = project.get('dates') or {}
    footprint = project.get('tech_footprint') or {}

    color = tier_color(tier, config)
    background = tier_row_background(tier, config)

    status_style = settings_module.STATUS_STYLES.get(status, settings_module.STATUS_FALLBACK)
    deadline_raw = dates.get('deadline_text') or dates.get('target_delivery') or 'N/A'
    deadline_type = str(dates.get('deadline_type', 'soft')).lower()
    deadline_style = settings_module.DEADLINE_STYLES.get(
        deadline_type, settings_module.DEADLINE_STYLES['soft'])

    reason = project.get('blocked_reason', '')
    tooltip = ''
    if status == 'blocked' and reason:
        tooltip = ('<div class="blocked-tooltip"><strong>⚠️ Blocked:</strong> '
                   f'{esc(reason)}</div>')

    platforms = ''.join(f'<span class="plat-tag">{esc(tag)}</span>'
                        for tag in ensure_list(footprint.get('platforms')))

    disabled = '' if project_tasks else ' disabled'
    bar = _summary_bar(project_tasks, timeline, tier, status, config)

    # Line 1: priority + title + actions · line 2: status + deadline · line 3: platforms
    return f'''<tr class="project-main-row" data-tier-child="{esc(tier)}" data-proj-id="{esc(project_id)}" style="background:{background}" draggable="true">
  <td class="sticky-col project-cell" style="border-left:5px solid {color};background:{background}">
    <div class="project-line project-line--head">
      <div class="project-identity">
        <span class="drag-handle" title="Drag to reorder">☰</span>
        <button type="button" class="proj-toggle-btn" id="btn-toggle-proj-{esc(project_id)}" data-action="toggle-project" data-project="{esc(project_id)}"{disabled}>▼</button>
        <span class="prio-badge">#{position}</span>
        <strong class="project-title" title="{esc(name)}">{esc(name)}</strong>
      </div>
      <button type="button" class="action-btn" title="Open notes, tags and actions" data-action="toggle-detail" data-project="{esc(project_id)}">⚙️ Info &amp; actions</button>
      <button type="button" class="action-btn action-btn--slate" title="Advanced edit (form + RAW)" data-action="advanced-edit-open" data-project="{esc(project_id)}">\U0001F6E0️ Advanced edit</button>
    </div>
    <div class="project-line project-line--meta">
      <div class="status-wrapper">
        <span class="status-pill" style="background:{status_style['bg']};color:{status_style['fg']}">{esc(status.upper())}</span>
        {tooltip}
      </div>
      <span class="deadline-pill" style="background:{deadline_style['bg']};color:{deadline_style['fg']}">\U0001F4C5 {esc(format_date_long(deadline_raw, config))} [{esc(deadline_type.upper())}]</span>
    </div>
    <div class="project-line project-line--platforms">{platforms}</div>
  </td>
  <td class="timeline-cell">
    <div class="timeline-row timeline-row--project" style="background-color:{background}">{bar}</div>
  </td>
</tr>'''


def _resource_row(project_id, tier, task, timeline, config):
    geometry = timeline.geometry(task['start'], task['end'])
    if not geometry:
        return ''

    left, width = geometry
    member = member_name(task['section'], task['label'], config)
    role = resolve_role(task['section'], task['label'], config)[0]
    color = role_color(task['section'], task['label'], task['type'], config)
    background = resource_row_background(tier, config)
    span = f"{format_date_long(task['start'], config)} → {format_date_long(task['end'], config)}"

    bar = (f'<div class="task-bar sub-bar" style="left:{left}px;width:{width}px;background:{color}" '
           f'title="{esc(task["label"])} — {esc(span)}">'
           f'<span class="bar-text">{esc(member)}</span></div>')

    return f'''<tr class="resource-sub-row" data-tier-child="{esc(tier)}" data-proj-child="{esc(project_id)}">
  <td class="sticky-col resource-cell" style="background:{background}">
    <div class="resource-line">
      <span class="resource-line__branch">└─</span>
      <span class="resource-line__role" style="color:{color}">{esc(role)}:</span>
      <span>{esc(member)}</span>
    </div>
  </td>
  <td class="timeline-cell">
    <div class="timeline-row timeline-row--resource" style="background-color:{background}">{bar}</div>
  </td>
</tr>'''


def _orphan_row(task, timeline, config):
    geometry = timeline.geometry(task['start'], task['end'])
    if not geometry:
        return ''

    left, width = geometry
    color = role_color(task['section'], task['label'], task['type'], config)
    background = resource_row_background(config.other_tier, config)
    bar = (f'<div class="task-bar sub-bar" style="left:{left}px;width:{width}px;background:{color}">'
           f'<span class="bar-text">{esc(task["label"])}</span></div>')

    return f'''<tr class="resource-sub-row" data-tier-child="{esc(config.other_tier)}">
  <td class="sticky-col resource-cell resource-cell--flat" style="background:{background}">
    <div class="resource-line"><strong>{esc(task["label"])}</strong></div>
  </td>
  <td class="timeline-cell">
    <div class="timeline-row timeline-row--resource" style="background-color:{background}">{bar}</div>
  </td>
</tr>'''
