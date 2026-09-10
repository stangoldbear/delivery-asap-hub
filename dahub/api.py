"""
API actions: each handler describes ONLY the mutation to apply.

Loading, serialising and writing the file are centralised in
`ProjectRepository.mutate`; the fields themselves are declared once in
`schema.py`. Adding an endpoint means registering a function in `ROUTES` —
the server never changes.
"""

from datetime import datetime

from . import schema
from .repository import csv_to_list


class ApiError(Exception):
    """An application error carrying the HTTP status to answer with."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ─── Mutations ───────────────────────────────────────────────────────────────
def _update_project(data, params, _now):
    """Quick edit: the fields exposed by the inline detail panel."""
    schema.apply_fields(data, params, schema.quick_fields())


def _advanced_update_project(data, params, _now):
    """
    Advanced edit: every field of the card schema.

    Fields absent from the payload are left untouched, so an editor that does
    not know about `todos` or `intro` cannot erase them.
    """
    schema.apply_fields(data, params, schema.advanced_fields())
    schema.apply_rows(data, params)


def _raw_update_project(repository, project_id, params):
    """Store the raw text (front matter + body) from the RAW editor."""
    text = params.get('raw_text')
    if not text or not str(text).strip():
        raise ApiError('The RAW text cannot be empty.')
    try:
        repository.write_raw(project_id, text)
    except ValueError as exc:
        raise ApiError(str(exc))


def _add_todo(data, params, now):
    text = str(params.get('text', '')).strip()
    if not text:
        raise ApiError('The note text is required.')

    todos = csv_to_list(data.get('todos'))
    todos.append({
        'id': f"todo-{data.get('id', 'project')}-{len(todos) + 1}-{int(now.timestamp())}",
        'text': text,
        'deadline': str(params.get('deadline', '')).strip(),
        'done': False,
    })
    data['todos'] = todos


def _update_todo(data, params, _now):
    todo_id = _require_todo_id(params)
    text = str(params.get('text', '')).strip()
    if not text:
        raise ApiError('The note text is required.')

    for collection in ('todos', 'todos_history'):
        for item in csv_to_list(data.get(collection)):
            if item.get('id') == todo_id:
                item['text'] = text
                item['deadline'] = str(params.get('deadline', '')).strip()
                return
    raise ApiError('Note not found.', status=404)


def _toggle_todo(data, params, now):
    todo_id = _require_todo_id(params)
    todos = csv_to_list(data.get('todos'))
    history = csv_to_list(data.get('todos_history'))

    for index, item in enumerate(todos):
        if item.get('id') == todo_id:
            done = todos.pop(index)
            done['done'] = True
            done['completed_at'] = now.strftime('%Y-%m-%d %H:%M')
            history.insert(0, done)
            break
    else:
        for index, item in enumerate(history):
            if item.get('id') == todo_id:
                reopened = history.pop(index)
                reopened['done'] = False
                reopened.pop('completed_at', None)
                todos.append(reopened)
                break
        else:
            raise ApiError('Note not found.', status=404)

    data['todos'] = todos
    data['todos_history'] = history


def _delete_todo(data, params, _now):
    todo_id = _require_todo_id(params)
    for collection in ('todos', 'todos_history'):
        if collection in data:
            data[collection] = [item for item in csv_to_list(data.get(collection))
                                if item.get('id') != todo_id]


def _require_todo_id(params):
    todo_id = params.get('todo_id')
    if not todo_id:
        raise ApiError('Missing `todo_id` parameter.')
    return todo_id


# ─── Routing table ───────────────────────────────────────────────────────────
ROUTES = {
    'update': _update_project,
    'advanced-update': _advanced_update_project,
    'todo/add': _add_todo,
    'todo/update': _update_todo,
    'todo/toggle': _toggle_todo,
    'todo/delete': _delete_todo,
}

# "Raw" actions bypass the parse → dict → dump round trip and work on the file
# text directly (used by the RAW tab of the advanced editor).
RAW_ROUTES = {
    'raw-update': _raw_update_project,
}

BATCH_ID = '_batch'


def _reorder_projects(repository, params, _now):
    """
    Apply a new ordering: `order` is a list of {id, tier} in display order.

    Priority is stored per tier, so the number in a card matches its rank
    inside its own tier.
    """
    order = params.get('order')
    if not isinstance(order, list):
        raise ApiError("Missing or invalid `order` parameter.")

    tiers = repository.settings.tiers
    position = {tier: 0 for tier in tiers}
    updated = 0

    for item in order:
        if not isinstance(item, dict):
            continue
        project_id, tier = item.get('id'), item.get('tier')
        if not project_id or not tier:
            continue
        if tier not in tiers:
            raise ApiError(f'Unknown tier: {tier}')
        if not repository.exists(project_id):
            continue

        position[tier] += 1

        def mutator(data, tier=tier, rank=position[tier]):
            data['tier'] = tier
            data['priority'] = str(rank)

        repository.mutate(project_id, mutator)
        updated += 1

    return {'updated': updated}


BATCH_ROUTES = {
    'reorder': _reorder_projects,
}


def dispatch(repository, project_id, action, params, *, now=None):
    """Run the requested action. Raises ApiError on invalid input."""
    now = now or datetime.now()

    try:
        if project_id == BATCH_ID:
            handler = BATCH_ROUTES.get(action)
            if handler is None:
                raise ApiError(f'Unknown batch action: {action}', status=404)
            result = handler(repository, params, now) or {}
            return {'success': True, 'action': action, **result}

        if action in RAW_ROUTES:
            _require_project(repository, project_id)
            RAW_ROUTES[action](repository, project_id, params)
            return {'success': True, 'project': project_id, 'action': action}

        mutator = ROUTES.get(action)
        if mutator is None:
            raise ApiError(f'Unknown action: {action}', status=404)
        _require_project(repository, project_id)

        repository.mutate(project_id, lambda data: mutator(data, params, now))
        return {'success': True, 'project': project_id, 'action': action}
    except schema.ValidationError as exc:
        raise ApiError(str(exc))


def _require_project(repository, project_id):
    if not repository.exists(project_id):
        raise ApiError(f'Project not found: {project_id}', status=404)
