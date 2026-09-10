"""
Deployment settings and presentation constants.

`settings.toml` holds everything an organisation changes (tiers, squads,
project codes, links, wording); this module parses it once, fails fast on a
malformed file, and exposes it as a frozen `Settings` value.

Composition root: `configure()` is called once by the entry point. Modules read
the result through `current()`. A single process-wide value is a deliberate
simplification for a single-tenant local tool — tests call `configure()` with
their own fixture path.
"""

import os
import tomllib
from dataclasses import dataclass
from datetime import date

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PACKAGE_DIR)
STATIC_DIR = os.path.join(PACKAGE_DIR, 'static')
DEFAULT_SETTINGS_PATH = os.path.join(BASE_DIR, 'settings.toml')
LOCAL_SETTINGS_PATH = os.path.join(BASE_DIR, 'settings.local.toml')

# ─── Presentation constants (not deployment-specific: kept in code) ──────────
TIER_ROW_ALPHA = 0.15
RESOURCE_ROW_ALPHA = 0.05
BLOCKED_COLOR = '#e74c3c'

STATUS_STYLES = {
    'active':   {'bg': '#e8f5e9', 'fg': '#2e7d32'},
    'blocked':  {'bg': '#ffebee', 'fg': '#b71c1c'},
    'inactive': {'bg': '#eceff1', 'fg': '#546e7a'},
}
STATUS_FALLBACK = {'bg': '#f5f5f5', 'fg': '#555555'}
STATUS_OPTIONS = list(STATUS_STYLES)

DEADLINE_STYLES = {
    'hard': {'bg': '#ffebee', 'fg': '#c62828'},
    'soft': {'bg': '#fff8e1', 'fg': '#f57f17'},
}
DEADLINE_OPTIONS = [('soft', 'Soft target'), ('hard', 'Hard deadline')]

SEVERITY_OPTIONS = ['high', 'medium', 'low']
QA_EFFORT_OPTIONS = ['low', 'medium', 'high']

# Gantt layout metrics. Emitted as CSS custom properties by the view so that
# stylesheet and script never restate them (single source of truth).
COL_W = 17           # day column width in px
LABEL_W = 340        # sticky left column, initial width
LABEL_W_MIN = 160    # drag limits for the sticky column
LABEL_W_MAX = 900
ROW_H = 62           # project row (three-line layout)
SUB_ROW_H = 20       # resource row


class SettingsError(Exception):
    """Raised when settings.toml is missing, malformed or inconsistent."""


@dataclass(frozen=True)
class Settings:
    title: str
    subtitle: str
    owner: str
    footer: str
    host: str
    port: int
    vault_root: str
    projects_dir: str
    plan_path: str
    jira_base_url: str
    jira_placeholder: str
    confluence_placeholder: str
    figma_placeholder: str
    chart_min_end: date
    months: tuple
    month_abbr: tuple
    tiers: dict            # key -> {'title': str, 'rgb': (r, g, b)}
    default_tier: str
    other_tier: str        # last declared tier: bucket for project-less tasks
    platforms: tuple
    roles: tuple           # ({'key','label','color','keywords'}, ...)
    fallback_role: dict
    time_off_color: str
    squads: dict           # section -> ({'prefix','name','role'}, ...)
    project_codes: dict    # short code -> project id

    @property
    def project_tiers(self):
        return [key for key in self.tiers if key != self.other_tier]

    def role(self, key):
        for entry in self.roles:
            if entry['key'] == key:
                return entry
        return self.fallback_role

    def css_variables(self):
        """Layout metrics shared with app.css / app.js."""
        return {
            '--col-w': f'{COL_W}px',
            '--label-w': f'{LABEL_W}px',
            '--label-w-min': f'{LABEL_W_MIN}px',
            '--label-w-max': f'{LABEL_W_MAX}px',
            '--row-h': f'{ROW_H}px',
            '--sub-row-h': f'{SUB_ROW_H}px',
        }


# ─── Colour helpers (single source of truth: RGB triples) ────────────────────
def hex_color(rgb):
    return '#%02x%02x%02x' % tuple(rgb)


def rgba(rgb, alpha):
    r, g, b = rgb
    return f'rgba({r}, {g}, {b}, {alpha})'


# ─── Parsing ─────────────────────────────────────────────────────────────────
def _require(mapping, key, where):
    if key not in mapping:
        raise SettingsError(f'Missing `{key}` in [{where}].')
    return mapping[key]


def _resolve(path, root=BASE_DIR):
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(root, path))


def _parse(raw, source):
    app = raw.get('app', {})
    server = raw.get('server', {})
    vault = raw.get('vault', {})
    links = raw.get('links', {})
    locale = raw.get('locale', {})
    defaults = raw.get('defaults', {})

    tiers_raw = raw.get('tiers') or []
    if not tiers_raw:
        raise SettingsError(f'{source}: at least one [[tiers]] entry is required.')

    tiers = {}
    for entry in tiers_raw:
        key = _require(entry, 'key', 'tiers')
        if key in tiers:
            raise SettingsError(f'{source}: duplicate tier key `{key}`.')
        rgb = _require(entry, 'rgb', f'tiers.{key}')
        if len(rgb) != 3 or not all(isinstance(c, int) and 0 <= c <= 255 for c in rgb):
            raise SettingsError(f'{source}: tier `{key}` rgb must be three ints 0-255.')
        tiers[key] = {'title': _require(entry, 'title', f'tiers.{key}'), 'rgb': tuple(rgb)}

    default_tier = defaults.get('tier', next(iter(tiers)))
    if default_tier not in tiers:
        raise SettingsError(f'{source}: defaults.tier `{default_tier}` is not a declared tier.')

    roles = tuple(
        {
            'key': _require(entry, 'key', 'roles'),
            'label': _require(entry, 'label', 'roles'),
            'color': _require(entry, 'color', 'roles'),
            'keywords': tuple(entry.get('keywords', ())),
        }
        for entry in raw.get('roles', [])
    )
    role_keys = {entry['key'] for entry in roles}

    squads = {}
    for squad in raw.get('squads', []):
        section = _require(squad, 'section', 'squads')
        members = []
        for member in squad.get('members', []):
            role_key = member.get('role')
            if role_key and role_key not in role_keys:
                raise SettingsError(
                    f'{source}: squad `{section}` references unknown role `{role_key}`.')
            members.append({
                'prefix': _require(member, 'prefix', f'squads.{section}'),
                'name': _require(member, 'name', f'squads.{section}'),
                'role': role_key,
            })
        # Longest prefix first: "iOS Dev #1" must win over a hypothetical "iOS".
        members.sort(key=lambda m: len(m['prefix']), reverse=True)
        squads[section] = tuple(members)

    months = tuple(locale.get('months', ()))
    month_abbr = tuple(locale.get('month_abbr', ()))
    if len(months) != 12 or len(month_abbr) != 12:
        raise SettingsError(f'{source}: [locale] months and month_abbr need 12 entries each.')

    min_end = raw.get('timeline', {}).get('min_end', date(date.today().year, 12, 31))
    if not isinstance(min_end, date):
        raise SettingsError(f'{source}: timeline.min_end must be a date (YYYY-MM-DD).')

    vault_root = _resolve(vault.get('root', '.knowledge'))

    return Settings(
        title=app.get('title', 'Delivery ASAP hub'),
        subtitle=app.get('subtitle', ''),
        owner=app.get('owner', ''),
        footer=app.get('footer', ''),
        host=server.get('host', '127.0.0.1'),
        port=int(server.get('port', 8080)),
        vault_root=vault_root,
        projects_dir=_resolve(vault.get('projects', '02-projects/active'), vault_root),
        plan_path=_resolve(vault.get('plan', '03-delivery-patterns/delivery-plan.md'), vault_root),
        jira_base_url=links.get('jira_base_url', ''),
        jira_placeholder=links.get('jira_placeholder', ''),
        confluence_placeholder=links.get('confluence_placeholder', ''),
        figma_placeholder=links.get('figma_placeholder', ''),
        chart_min_end=min_end,
        months=months,
        month_abbr=month_abbr,
        tiers=tiers,
        default_tier=default_tier,
        other_tier=list(tiers)[-1],
        platforms=tuple(defaults.get('platforms', ())),
        roles=roles,
        fallback_role=dict(defaults.get('fallback_role', {'label': 'Member', 'color': '#78909c'})),
        time_off_color=defaults.get('time_off_color', '#ef5350'),
        squads=squads,
        project_codes=dict(raw.get('project_codes', {})),
    )


def load(path=None):
    """Read and validate a settings file. Raises SettingsError, never guesses."""
    if path is None:
        path = LOCAL_SETTINGS_PATH if os.path.isfile(LOCAL_SETTINGS_PATH) else DEFAULT_SETTINGS_PATH
    try:
        with open(path, 'rb') as handle:
            raw = tomllib.load(handle)
    except FileNotFoundError:
        raise SettingsError(f'Settings file not found: {path}')
    except tomllib.TOMLDecodeError as exc:
        raise SettingsError(f'{path}: invalid TOML — {exc}')
    return _parse(raw, os.path.basename(path))


def _rebase(path, old_root, new_root):
    """Move a vault path under a different vault root, keeping its shape."""
    try:
        relative = os.path.relpath(path, old_root)
    except ValueError:
        return path
    if relative.startswith(os.pardir):
        return path
    return os.path.normpath(os.path.join(new_root, relative))


_current = None


def configure(path=None, *, vault=None, projects_dir=None, plan_path=None,
              host=None, port=None):
    """Load settings once, applying command-line overrides. Returns the value."""
    global _current
    settings = load(path)
    overrides = {}
    if vault:
        root = _resolve(vault, os.getcwd())
        overrides['vault_root'] = root
        overrides['projects_dir'] = _rebase(settings.projects_dir, settings.vault_root, root)
        overrides['plan_path'] = _rebase(settings.plan_path, settings.vault_root, root)
    if projects_dir:
        overrides['projects_dir'] = _resolve(projects_dir, os.getcwd())
    if plan_path:
        overrides['plan_path'] = _resolve(plan_path, os.getcwd())
    if host:
        overrides['host'] = host
    if port is not None:
        overrides['port'] = int(port)
    if overrides:
        settings = Settings(**{**settings.__dict__, **overrides})
    _current = settings
    return settings


def current():
    """Settings for this process; loads the default file on first use."""
    if _current is None:
        configure()
    return _current
