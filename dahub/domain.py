"""
Domain logic: dates, tiers, roles, gantt parsing, timeline calendar.

Pure and testable: no I/O, no HTML, and no hidden clock — "today" is passed
in so every rendering decision can be reproduced in a test.
"""

import re
from datetime import date, datetime, timedelta

from . import settings as settings_module

_ISO_DATE_RE = re.compile(r'^(\d{4})[/-](\d{1,2})[/-](\d{1,2})(?:[ T](\d{1,2}:\d{2}))?$')
_EU_DATE_RE = re.compile(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})(?:[ T](\d{1,2}:\d{2}))?$')
_GANTT_KEYWORDS = ('gantt', 'title', 'dateFormat', 'axisFormat', 'tickInterval', 'excludes')
_DURATION_RE = re.compile(r'^\d+d$')
_PLAN_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}')


def _settings(settings=None):
    return settings or settings_module.current()


# ─── Dates ───────────────────────────────────────────────────────────────────
def format_date_long(value, settings=None):
    """
    Spell a date out: `24 August 26`.

    Accepts date/datetime, ISO (`2026-08-24`) and EU (`24/08/2026`). Any other
    text is returned untouched, so free-form deadlines ("mid September") survive.
    """
    if not value:
        return ''

    config = _settings(settings)
    if isinstance(value, (datetime, date)):
        return _compose(config, value.day, value.month, str(value.year))

    text = str(value).strip()

    iso = _ISO_DATE_RE.match(text)
    if iso:
        return _compose(config, int(iso.group(3)), int(iso.group(2)), iso.group(1), iso.group(4))

    eu = _EU_DATE_RE.match(text)
    if eu:
        return _compose(config, int(eu.group(1)), int(eu.group(2)), eu.group(3), eu.group(4))

    return text


def _compose(config, day, month, year, clock=None):
    if not 1 <= month <= 12:
        return f'{day}/{month}/{year}'
    result = f'{day} {config.months[month - 1]} {str(year)[-2:]}'
    return f'{result}, {clock}' if clock else result


# ─── Tiers ───────────────────────────────────────────────────────────────────
def tier_key(project, settings=None):
    config = _settings(settings)
    key = str(project.get('tier', config.default_tier)).lower()
    return key if key in config.tiers else config.default_tier


def tier_rgb(key, settings=None):
    config = _settings(settings)
    return config.tiers.get(key, config.tiers[config.default_tier])['rgb']


def tier_color(key, settings=None):
    return settings_module.hex_color(tier_rgb(key, settings))


def tier_row_background(key, settings=None):
    """Tier colour at low alpha, for the project row background."""
    return settings_module.rgba(tier_rgb(key, settings), settings_module.TIER_ROW_ALPHA)


def resource_row_background(key, settings=None):
    """Tier colour at very low alpha, for resource rows and detail panels."""
    return settings_module.rgba(tier_rgb(key, settings), settings_module.RESOURCE_ROW_ALPHA)


def tier_title(key, settings=None):
    config = _settings(settings)
    return config.tiers.get(key, config.tiers[config.default_tier])['title']


def summary_bar_color(key, status, settings=None):
    if status == 'blocked':
        return settings_module.BLOCKED_COLOR
    return tier_color(key, settings)


def group_by_tier(projects, settings=None):
    """Group projects by tier, preserving the declaration order of settings."""
    config = _settings(settings)
    grouped = {key: [] for key in config.tiers}
    for project in projects:
        grouped[tier_key(project, config)].append(project)
    return grouped


# ─── Roles and people ────────────────────────────────────────────────────────
def resolve_member(section, label, settings=None):
    """
    The person a timeline row belongs to, matched on the label prefix.

    Returns the squad entry (name + role) or None. Prefixes are matched
    longest-first, so `iOS Dev #10` never resolves as `iOS Dev #1`.
    """
    config = _settings(settings)
    for member in config.squads.get(section, ()):
        if label.startswith(member['prefix']):
            return member
    return None


def resolve_role(section, label, settings=None):
    """
    Return (role_label, colour) for a timeline row.

    The squad roster wins: it is explicit. Keyword rules only cover rows with
    no matching member, so a task named "iOS: call the Server API" cannot be
    mislabelled as backend work.
    """
    config = _settings(settings)
    member = resolve_member(section, label, config)
    if member and member.get('role'):
        role = config.role(member['role'])
        return role['label'], role['color']

    haystack = f'{section} {label}'
    for role in config.roles:
        if any(word in haystack for word in role['keywords']):
            return role['label'], role['color']
    fallback = config.fallback_role
    return fallback['label'], fallback['color']


def member_name(section, label, settings=None, default='Resource'):
    member = resolve_member(section, label, settings)
    return member['name'] if member else default


def role_color(section, label, task_type, settings=None):
    if task_type == 'done':          # time off
        return _settings(settings).time_off_color
    return resolve_role(section, label, settings)[1]


# ─── Delivery plan (mermaid gantt) ───────────────────────────────────────────
def _add_working_days(start, count):
    end, counted = start, 0
    while counted < count:
        end += timedelta(days=1)
        if end.weekday() < 5:
            counted += 1
    return end


def _match_project(label, settings=None):
    for code, project_id in _settings(settings).project_codes.items():
        if re.search(r'\b' + re.escape(code) + r'\b', label):
            return project_id
    return None


def _split_task_line(line):
    marker = line.rfind(' :')
    if marker != -1:
        return line[:marker].strip(), line[marker + 2:].strip()
    marker = line.find(':')
    if marker == -1:
        return None, None
    return line[:marker].strip(), line[marker + 1:].strip()


def _task_type(modifiers):
    for candidate in ('done', 'crit', 'active'):
        if candidate in modifiers:
            return candidate
    return 'default'


def parse_gantt(gantt_code, settings=None):
    """Turn a mermaid gantt block into structured tasks."""
    config = _settings(settings)
    tasks = []
    section = 'Default'

    for raw in gantt_code.split('\n'):
        line = raw.strip()
        if not line or line.startswith(_GANTT_KEYWORDS) or line.startswith('%%'):
            continue
        if line.startswith('section '):
            section = line[8:].strip()
            continue

        label, remainder = _split_task_line(line)
        if label is None:
            continue

        modifiers, date_parts = [], []
        for part in (piece.strip() for piece in remainder.split(',')):
            if _PLAN_DATE_RE.match(part) or _DURATION_RE.match(part):
                date_parts.append(part)
            else:
                modifiers.extend(part.split())

        if not date_parts:
            continue

        try:
            start = datetime.strptime(date_parts[0], '%Y-%m-%d')
            if len(date_parts) > 1:
                duration = date_parts[1]
                end = (_add_working_days(start, int(duration[:-1]))
                       if _DURATION_RE.match(duration)
                       else datetime.strptime(duration, '%Y-%m-%d'))
            else:
                end = start + timedelta(days=1)
        except ValueError:
            continue

        tasks.append({
            'label': label,
            'section': section,
            'start': start,
            'end': end,
            'type': _task_type(modifiers),
            'project_id': _match_project(label, config),
        })

    return tasks


# ─── Timeline calendar ───────────────────────────────────────────────────────
class Timeline:
    """Working days, grouped months and bar geometry for the gantt chart."""

    def __init__(self, tasks, *, settings=None, col_width=None, hide_past=False, today=None):
        config = _settings(settings)
        self.col_width = col_width or settings_module.COL_W
        self.today = today or date.today()
        self.hide_past = hide_past
        self.days = self._build_days(tasks, config.chart_min_end, hide_past, self.today)
        self.months = self._group_months(self.days)
        self.width = len(self.days) * self.col_width

    @staticmethod
    def _build_days(tasks, min_end, hide_past, today):
        bounds = [task['start'] for task in tasks] + [task['end'] for task in tasks]
        if not bounds:
            reference = datetime.combine(today, datetime.min.time())
            bounds = [reference, reference + timedelta(days=30)]

        start = min(bounds)
        start -= timedelta(days=start.weekday())            # snap to Monday
        end = max(max(bounds), datetime.combine(min_end, datetime.min.time()))

        days, cursor = [], start
        while cursor <= end:
            if cursor.weekday() < 5:                        # working days only
                days.append(cursor)
            cursor += timedelta(days=1)

        if hide_past:
            days = [day for day in days if day.date() >= today]
        return days

    @staticmethod
    def _group_months(days):
        months, current, count = [], None, 0
        for day in days:
            key = (day.year, day.month)
            if key != current:
                if current:
                    months.append((current, count))
                current, count = key, 1
            else:
                count += 1
        if current:
            months.append((current, count))
        return months

    def geometry(self, start, end):
        """(left, width) of a bar in px, or None when it falls outside the scale."""
        first = next((i for i, day in enumerate(self.days) if day.date() >= start.date()), None)
        if first is None:
            return None
        last = next((i for i, day in enumerate(self.days) if day.date() >= end.date()),
                    len(self.days))
        left = first * self.col_width + 2
        width = max((last - first) * self.col_width - 4, self.col_width - 4)
        return left, width

    @property
    def grid_background(self):
        return ('repeating-linear-gradient(to right, #808080 0, #808080 1px, '
                f'transparent 1px, transparent {self.col_width}px)')

    def day_state(self, day):
        """Classify a day against today: 'past' | 'today' | 'future'."""
        value = day.date()
        if value < self.today:
            return 'past'
        if value == self.today:
            return 'today'
        return 'future'

    @property
    def today_index(self):
        for index, day in enumerate(self.days):
            if day.date() == self.today:
                return index
        return None
