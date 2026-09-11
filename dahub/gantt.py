"""
Gantt chart rendering: header, tier rows, project rows, resource rows.

Geometry and colours come from `domain`; layout metrics travel as CSS custom
properties, so the stylesheet and the resize script never restate them.

A tier reaches the markup as one custom property, `--tier`, set on the row: the
stylesheet decides how much of it to spend (a rail and a marker), and the
timeline lane beside it never takes it at all.
"""

from . import settings as settings_module
from .domain import (
    format_date_long,
    group_by_display,
    group_color,
    group_order,
    group_title,
    is_display_group,
    project_milestones,
    project_span,
    project_tasks,
    summary_bar_color,
    tier_color,
    tier_key,
)
from .markup import attrs, esc, icon

CARET_OPEN = '▲'
CARET_CLOSED = '►'


def render(projects, timeline, *, detail_row, settings=None):
    """
    The whole chart as one `<table>`.

    Every bar comes from the card that owns it: the chart asks a project for
    its span and its rows and draws them. `detail_row(project, tier)` is
    injected, so the chart places the expandable panel but knows nothing about
    its contents.
    """
    config = settings or settings_module.current()
    grouped = group_by_display(projects, config)

    parts = [_header(timeline, config)]

    for group in group_order(config):
        members = grouped.get(group, [])
        # An empty tier is not drawn; DONE and DROPPED always are, because a
        # project is finished by being dragged onto them.
        if not members and not is_display_group(group):
            continue

        parts.append(_group_header(group, len(members), config))
        for project in members:
            parts.extend(_project_block(project, group, timeline, detail_row, config))

    parts.append('</tbody></table></div>')
    return '\n'.join(parts)


def _day_classes(day, timeline):
    """
    The calendar header boxes every Monday-to-Friday run.

    The weekday reads from the box rather than from a printed letter, and a
    week cut in half by the start or the end of the scale is closed off where
    it is cut.
    """
    classes = ['day-cell', f'day-cell--{timeline.day_state(day)}']
    if day.weekday() >= 5:
        classes.append('day-cell--weekend')
        return classes

    classes.append('day-cell--wd')
    if day.weekday() == 0 or day == timeline.days[0]:
        classes.append('day-cell--w-start')
    if day.weekday() == 4 or day == timeline.days[-1]:
        classes.append('day-cell--w-end')
    return classes


def _header(timeline, config):
    months = ''.join(
        f'<div class="month-cell" style="width:calc(var(--col-w) * {count})">'
        f'{config.month_abbr[month - 1]} {year}</div>'
        for (year, month), count in timeline.months
    )
    # The date travels with the cell: it is what turns a click at an x offset
    # in a lane into the day the pointer is over.
    days = ''.join(
        f'<div class="{" ".join(_day_classes(day, timeline))}" '
        f'data-date="{day.strftime("%Y-%m-%d")}">{day.day}</div>'
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
        <div class="label-head__title">Project &amp; assigned resources</div>
      </th>
      <th class="timeline-head">
        <div class="timeline-strip">{months}</div>
      </th>
    </tr>
    <tr>
      <th class="label-head sticky-col"></th>
      <th class="timeline-head">
        <div class="timeline-strip">{days}</div>
      </th>
    </tr>
  </thead>
  <tbody>'''


def _group_header(group, count, config):
    title = group_title(group, config)
    return f'''<tr class="tier-row" data-group="{esc(group)}" style="--tier:{group_color(group, config)}">
  <td class="sticky-col tier-row__cell">
    <div class="tier-row__inner">
      <button type="button" class="btn btn--ghost btn--sm btn--icon" id="btn-group-{esc(group)}" data-action="toggle-group" data-group="{esc(group)}" title="Collapse or expand this group" aria-label="Collapse or expand {esc(title)}">{CARET_OPEN}</button>
      <span class="tier-row__marker"></span>
      <span class="tier-row__title">{esc(title)}</span>
      <span class="badge">{count}</span>
    </div>
  </td>
  <td class="tier-row__band"></td>
</tr>'''


def _project_block(project, group, timeline, detail_row, config):
    rows_of_project = project_tasks(project, config)
    rail = tier_color(tier_key(project, config), config)

    rows = [_project_row(project, group, rows_of_project, timeline, config)]
    rows.extend(_resource_row(project['id'], group, rail, task, timeline, config)
                for task in rows_of_project)
    rows.append(detail_row(project, group))
    return rows


def _summary_bar(project, timeline, status, config):
    span = project_span(project, config)
    if not span:
        return ''
    start, end = span
    geometry = timeline.geometry(start, end)
    if not geometry:
        return ''
    left, width = geometry
    fill = summary_bar_color(tier_key(project, config), status, config)
    blocked = ' summary-bar--blocked' if status == 'blocked' else ''
    span = (f'{format_date_long(start, config)} → {format_date_long(end, config)}')
    return (f'<div class="task-bar summary-bar{blocked}" style="left:{left}px;width:{width}px;'
            f'background:{fill}" title="Project span: {esc(span)}"'
            f'{attrs(project=project["id"])} data-start="{start.strftime("%Y-%m-%d")}" '
            f'data-end="{end.strftime("%Y-%m-%d")}">{_grips()}</div>')


def _project_row(project, group, rows_of_project, timeline, config):
    project_id = project['id']
    name = project.get('name', project_id)
    status = str(project.get('status', 'active')).lower()
    dates = project.get('dates') or {}

    status_style = settings_module.STATUS_STYLES.get(status, settings_module.STATUS_FALLBACK)
    deadline_raw = dates.get('deadline_text') or dates.get('target_delivery') or 'N/A'
    deadline_type = str(dates.get('deadline_type', 'soft')).lower()
    deadline_style = settings_module.DEADLINE_STYLES.get(
        deadline_type, settings_module.DEADLINE_STYLES['soft'])

    reason = project.get('blocked_reason', '')
    tooltip = ''
    if status == 'blocked' and reason:
        tooltip = f'<span class="blocked-tooltip"><strong>Blocked:</strong> {esc(reason)}</span>'

    disabled = '' if rows_of_project else ' disabled'
    bar = _summary_bar(project, timeline, status, config)
    warning = _warning(any(task['outside'] for task in rows_of_project),
                       'A task on this project falls outside the span it declares')

    # One line: identity, then the two things that change (status, deadline),
    # then the row actions, which only appear on hover or keyboard focus.
    # The platform tags left the chart entirely — the detail panel lists them.
    return f'''<tr class="project-main-row" data-group-child="{esc(group)}" data-proj-id="{esc(project_id)}" style="--tier:{tier_color(tier_key(project, config), config)}" draggable="true">
  <td class="sticky-col project-cell">
    <div class="project-line project-line--head">
      <div class="project-identity">
        <span class="drag-handle" title="Drag to reorder">{icon('grip')}</span>
        <button type="button" class="btn btn--ghost btn--sm btn--icon" id="btn-toggle-proj-{esc(project_id)}" data-action="toggle-project" data-project="{esc(project_id)}" title="Collapse or expand the resources" aria-label="Collapse or expand the resources of {esc(name)}"{disabled}>{CARET_OPEN}</button>
        <span class="prio-badge">{esc(project.get('priority', ''))}</span>
        <strong class="project-title" title="{esc(project_id)}">{esc(name)}</strong>{warning}
      </div>
      <span class="project-row__signals">
        <span class="status-wrapper" tabindex="0">
          <span class="status-pill" style="background:{status_style['bg']};color:{status_style['fg']}">{esc(status.upper())}</span>
          {tooltip}
        </span>
        <span class="deadline-pill" style="background:{deadline_style['bg']};color:{deadline_style['fg']}">{esc(format_date_long(deadline_raw, config))} [{esc(deadline_type.upper())}]</span>
      </span>
      <span class="project-row__actions">
        <button type="button" class="btn btn--ghost btn--sm btn--icon" title="Notes &amp; actions" aria-label="Notes and actions for {esc(name)}" data-action="toggle-detail" data-project="{esc(project_id)}">{icon('panel')}</button>
        <button type="button" class="btn btn--ghost btn--sm btn--icon" title="Advanced edit" aria-label="Advanced edit of {esc(name)}" data-action="advanced-edit-open" data-project="{esc(project_id)}">{icon('sliders')}</button>
      </span>
    </div>
  </td>
  <td class="timeline-cell">
    <div class="timeline-row timeline-row--project" data-lane="{esc(project_id)}">{bar}{_milestones(project, timeline, config)}</div>
  </td>
</tr>'''


def _milestones(project, timeline, config):
    """
    The one motif of the interface, used for the one thing it means: a date
    that matters. Centred on its day, and never hidden behind a bar.
    """
    marks = []
    for mark in project_milestones(project, config):
        geometry = timeline.geometry(mark['date'], mark['date'])
        if not geometry:
            continue
        left = geometry[0] + (settings_module.COL_W / 2) - 2
        label = f"{format_date_long(mark['date'], config)}"
        if mark['text']:
            label += f" — {mark['text']}"
        marks.append(
            f'<button type="button" class="milestone" style="left:{left:.0f}px" '
            f'title="{esc(label)}" aria-label="{esc(label)}" data-action="milestone-open"'
            f'{attrs(project=project["id"], milestone=mark["id"], text=mark["text"])}'
            f' data-date="{mark["date"].strftime("%Y-%m-%d")}">{icon("diamond")}</button>')
    return ''.join(marks)


def _grips():
    """The two edges a bar can be resized from; the middle moves the whole bar."""
    return ('<span class="bar-grip bar-grip--start" data-grip="start"></span>'
            '<span class="bar-grip bar-grip--end" data-grip="end"></span>')


def _warning(condition, message):
    """A row that does not add up says so, and says what does not add up."""
    if not condition:
        return ''
    return (f'<span class="row-warning" title="{esc(message)}" '
            f'aria-label="{esc(message)}">{icon("warning")}</span>')


def _resource_row(project_id, group, rail, task, timeline, config):
    geometry = timeline.geometry(task['start'], task['end'])
    if not geometry:
        return ''

    left, width = geometry
    color = task['color']
    span = f"{format_date_long(task['start'], config)} → {format_date_long(task['end'], config)}"
    label = task['note'] or task['who']
    classes = 'task-bar sub-bar' + (f' sub-bar--{task["type"]}' if task['type'] != 'default' else '')

    bar = (f'<div class="{classes}" style="left:{left}px;width:{width}px;background:{color}" '
           f'title="{esc(label)} — {esc(span)}"'
           f'{attrs(project=project_id, task=task["id"])} '
           f'data-start="{task["start"].strftime("%Y-%m-%d")}" '
           f'data-end="{task["end"].strftime("%Y-%m-%d")}">'
           f'<span class="bar-text">{esc(task["who"])}</span>{_grips()}</div>')

    return f'''<tr class="resource-sub-row" data-group-child="{esc(group)}" data-proj-child="{esc(project_id)}" style="--tier:{rail}">
  <td class="sticky-col resource-cell">
    <div class="resource-line">
      <span class="resource-line__branch">└─</span>
      <span class="resource-line__role" style="color:{color}">{esc(task['role'])}:</span>
      <span>{esc(task['who'])}</span>
      {_warning(task['outside'], 'This task falls outside the span its project declares')}
    </div>
  </td>
  <td class="timeline-cell">
    <div class="timeline-row timeline-row--resource">{bar}</div>
  </td>
</tr>'''
