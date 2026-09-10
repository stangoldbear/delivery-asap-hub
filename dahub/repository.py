"""
Data access: reads and writes the project cards in the knowledge vault.

The only module that touches the filesystem. View, domain and API know
nothing about paths or file format.
"""

import glob
import os
import re
import tempfile

from . import settings as settings_module
from .frontmatter import build_document, parse_frontmatter

_MERMAID_RE = re.compile(r'```mermaid\n(.*?)\n```', re.DOTALL)


def write_atomic(path, text):
    """
    Replace a file's content without ever leaving a truncated file behind.

    Writing in place truncates immediately: an error halfway through would
    destroy a knowledge card. Write a sibling temp file, then rename.
    """
    directory = os.path.dirname(path) or '.'
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        'w', encoding='utf-8', dir=directory, prefix='.tmp-', delete=False)
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise


class ProjectRepository:
    """Markdown + front matter cards, one file per project."""

    def __init__(self, directory=None, settings=None):
        self._settings = settings
        self.directory = directory or self.settings.projects_dir

    @property
    def settings(self):
        return self._settings or settings_module.current()

    # ─── Paths ───────────────────────────────────────────────────────────────
    def path_for(self, project_id):
        # Path traversal guard: only a plain file name is ever accepted.
        safe_id = os.path.basename(str(project_id))
        return os.path.join(self.directory, safe_id + '.md')

    def exists(self, project_id):
        return os.path.isfile(self.path_for(project_id))

    # ─── Reads ───────────────────────────────────────────────────────────────
    def load(self, project_id):
        """Return (data, body), or (None, None) when the card is missing."""
        path = self.path_for(project_id)
        if not os.path.isfile(path):
            return None, None
        with open(path, 'r', encoding='utf-8') as handle:
            return parse_frontmatter(handle.read())

    def read_raw(self, project_id):
        """Return the file text (front matter + body), or None."""
        path = self.path_for(project_id)
        if not os.path.isfile(path):
            return None
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read()

    def list_all(self):
        """Every card, ordered by tier declaration order then priority."""
        if not os.path.isdir(self.directory):
            return []

        projects = []
        for path in sorted(glob.glob(os.path.join(self.directory, '*.md'))):
            try:
                with open(path, 'r', encoding='utf-8') as handle:
                    data, body = parse_frontmatter(handle.read())
            except OSError as exc:
                print('Could not read project card:', path, exc)
                continue

            if not data:
                continue

            data['_body'] = body
            data['_file'] = os.path.basename(path)
            data['_prio_num'] = as_int(data.get('priority'), 99)
            projects.append(data)

        order = list(self.settings.tiers)
        default_rank = order.index(self.settings.default_tier)
        projects.sort(key=lambda project: (
            _rank(order, str(project.get('tier', '')).lower(), default_rank),
            project.get('_prio_num', 99),
            str(project.get('id', '')),
        ))
        return projects

    def load_plan(self):
        """The mermaid gantt block of the delivery plan, or '' when absent."""
        path = self.settings.plan_path
        if not os.path.isfile(path):
            return ''
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                match = _MERMAID_RE.search(handle.read())
        except OSError:
            return ''
        return match.group(1).strip() if match else ''

    # ─── Writes ──────────────────────────────────────────────────────────────
    def save(self, project_id, data, body=''):
        payload = {key: value for key, value in data.items() if not key.startswith('_')}
        write_atomic(self.path_for(project_id), build_document(payload, body))

    def write_raw(self, project_id, text):
        """
        Write raw text (front matter + body) after validating it.

        The text must contain a `---...---` block that parses back: a syntax
        error in the RAW editor must never reach the file.
        """
        data, _ = parse_frontmatter(text)
        if not data:
            raise ValueError('The YAML front matter is missing, empty or invalid.')
        write_atomic(self.path_for(project_id), text if text.endswith('\n') else text + '\n')

    def mutate(self, project_id, mutator):
        """
        Load → apply `mutator(data)` → save.

        Single write path: every API endpoint describes only *what* changes,
        never *how* it is persisted. Returns True when the card existed.
        """
        data, body = self.load(project_id)
        if data is None:
            return False
        mutator(data)
        # Convention: a mutator replaces the markdown body by setting the
        # private `_new_body` key (used by the advanced editor).
        if '_new_body' in data:
            body = data.pop('_new_body')
        self.save(project_id, data, body)
        return True


# ─── Shared helpers ──────────────────────────────────────────────────────────
def _rank(order, tier, default_rank):
    return order.index(tier) if tier in order else default_rank


def as_int(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def ensure_dict(data, key):
    """Guarantee that `data[key]` is a dict and return it."""
    if not isinstance(data.get(key), dict):
        data[key] = {}
    return data[key]


def csv_to_list(value):
    """
    Coerce an API value to a list, splitting a comma-separated string.

    Boundary coercion only: forms submit either a real array or a CSV field.
    For rendering use `view.ensure_list`, which never splits.
    """
    if value is None or value == '':
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(',') if item.strip()]
    if isinstance(value, list):
        return value
    return [value]
