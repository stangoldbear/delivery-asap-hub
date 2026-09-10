"""
HTML primitives shared by the view modules.

Rule for every renderer: user data reaches the browser only through escaped
text or escaped `data-*` attributes, never inside executable code.
"""

import html


def esc(value):
    """Escape for both text content and attribute values."""
    return html.escape('' if value is None else str(value), quote=True)


def ensure_list(value):
    """
    Wrap a value in a list for rendering, without ever splitting a string.

    The API boundary uses `repository.csv_to_list`, which does split: keep the
    two apart, a rendered value must survive commas untouched.
    """
    if not value:
        return []
    return [value] if isinstance(value, str) else list(value)


def attrs(**data):
    """Render `data-*` attributes from keyword arguments (underscores → dashes)."""
    return ''.join(f' data-{key.replace("_", "-")}="{esc(value)}"'
                   for key, value in data.items() if value is not None)


def select(select_id, options, current, project_id, css_class='form-input'):
    """A `<select>` whose current value is always representable.

    An out-of-vocabulary stored value is shown as a disabled option instead of
    silently displaying the first choice — otherwise the next save would
    overwrite the real value with something the user never picked.
    """
    values = [value for value, _ in options]
    choices = ''
    if current and current not in values:
        choices += (f'<option value="{esc(current)}" selected disabled>'
                    f'{esc(current)} (invalid)</option>')
    choices += ''.join(
        f'<option value="{esc(value)}"{" selected" if value == current else ""}>'
        f'{esc(label)}</option>'
        for value, label in options
    )
    return (f'<select id="{esc(select_id)}" class="{css_class}" '
            f'data-change="project-field" data-project="{esc(project_id)}">{choices}</select>')


def safe_url(value):
    """Return the URL only when it uses a scheme a link may safely open."""
    text = str(value or '').strip()
    lowered = text.lower()
    if lowered.startswith(('http://', 'https://')):
        return text
    if text and '://' not in text and not lowered.startswith(('javascript:', 'data:', 'vbscript:')):
        return text          # relative path or bare ticket key resolved by a base URL
    return ''
