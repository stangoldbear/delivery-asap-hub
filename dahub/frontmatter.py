"""
Minimal YAML front matter reader/writer for the markdown knowledge cards.

Single responsibility: text ⇄ Python data. No HTTP, no HTML, no paths.

It implements the subset the cards actually use — nested maps, lists of
scalars, lists of single-level maps, block scalars — and is deliberately
strict about nothing else, because the cards are also hand-edited: anything
the reader cannot represent would be silently destroyed by the next save.
"""

import re

_FRONTMATTER_RE = re.compile(r'^---\n(.*?)\n---(.*)', re.DOTALL)
_BLOCK_HEADERS = {'|', '|-', '|+', '>', '>-', '>+'}
_URL_SCHEME_RE = re.compile(r'^[\w.+-]+://')


def strip_comment(raw):
    """
    Drop a trailing `# comment` from a scalar, YAML-style.

    A `#` only starts a comment at the start of the value or after a space,
    and never inside a quoted string — so `"a # b"` and `http://x/#frag`
    keep their hash.
    """
    value = raw.strip()
    if value[:1] in ('"', "'"):
        quote = value[0]
        end = value.find(quote, 1)
        while end != -1 and value[end - 1] == '\\':
            end = value.find(quote, end + 1)
        if end != -1:
            return value[:end + 1].strip()
        return value
    hash_at = value.find('#')
    while hash_at != -1:
        if hash_at == 0 or value[hash_at - 1] in ' \t':
            return value[:hash_at].strip()
        hash_at = value.find('#', hash_at + 1)
    return value


def _coerce(raw):
    """Normalise a YAML scalar into a Python value."""
    value = strip_comment(raw)
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        # Quoted string: drop the delimiters and undo the escapes `_scalar`
        # produces (quotes and newlines).
        value = value[1:-1].replace('\\"', '"').replace('\\n', '\n')
    else:
        value = value.strip("'")
    lowered = value.lower()
    if lowered == 'true':
        return True
    if lowered == 'false':
        return False
    return value


def _next_line_is_list(lines, index):
    for line in lines[index + 1:]:
        if line.strip():
            return line.strip().startswith('- ')
    return False


def _read_block_scalar(lines, index, key_indent, header):
    """
    Collect the body of a `key: |` block starting after `index`.

    Returns (text, next_index). Trailing newline follows the chomping
    indicator: `|` keeps one, `|-` strips it, `|+` keeps them all.
    """
    body, cursor = [], index + 1
    while cursor < len(lines):
        line = lines[cursor]
        if line.strip() and (len(line) - len(line.lstrip())) <= key_indent:
            break
        body.append(line)
        cursor += 1

    while body and not body[-1].strip():
        body.pop()
    if not body:
        return '', cursor

    indent = min(len(line) - len(line.lstrip()) for line in body if line.strip())
    text = '\n'.join(line[indent:] if line.strip() else '' for line in body)
    if header.startswith('>'):
        text = text.replace('\n', ' ')
    if not header.endswith('-'):
        text += '\n'
    return text, cursor


def parse_yaml_text(text):
    """Convert an indented YAML subset into a nested dict."""
    data = {}
    stack = [(data, -1)]
    lines = text.split('\n')
    index = 0

    while index < len(lines):
        line = lines[index]
        index += 1
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        indent = len(line) - len(line.lstrip())
        while len(stack) > 1 and indent <= stack[-1][1]:
            stack.pop()
        parent = stack[-1][0]

        # List item
        if stripped.startswith('- '):
            if not isinstance(parent, list):
                continue
            item = stripped[2:].strip()
            # A quoted scalar or a URL is never an inline map, even though it
            # contains `:` — only an unquoted `key: value` is.
            is_inline_map = (
                ':' in item
                and not item.startswith(('{', '[', '"', "'"))
                and not _URL_SCHEME_RE.match(item)
            )
            if is_inline_map:
                key, raw = item.split(':', 1)
                entry = {key.strip(): _coerce(raw)}
                parent.append(entry)
                stack.append((entry, indent))
            else:
                parent.append(_coerce(item))
            continue

        if ':' not in stripped:
            continue

        key, raw = stripped.split(':', 1)
        key, raw = key.strip(), raw.strip()

        if raw in _BLOCK_HEADERS:
            parent[key], index = _read_block_scalar(lines, index - 1, indent, raw)
        elif not raw or strip_comment(raw) == '':
            container = [] if _next_line_is_list(lines, index - 1) else {}
            parent[key] = container
            stack.append((container, indent))
        elif raw.startswith('[') and raw.endswith(']'):
            parent[key] = [_coerce(x) for x in raw[1:-1].split(',') if x.strip()]
        elif raw.startswith('{') and raw.endswith('}'):
            parent[key] = {}
        else:
            parent[key] = _coerce(raw)

    return data


def parse_frontmatter(content):
    """Return (front_matter_data, markdown_body)."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content.strip()
    return parse_yaml_text(match.group(1)), match.group(2).strip()


def _scalar(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None:
        return '""'
    text = str(value).replace('"', '\\"')
    # Real newlines would break the line-oriented reader: inside a list row
    # they are escaped as a literal `\n` and restored by `_coerce`. Multi-line
    # values in map context are written as block scalars instead (see below).
    return '"' + text.replace('\n', '\\n') + '"'


def _block_scalar(value, indent):
    pad = ' ' * (indent + 2)
    header = '|' if value.endswith('\n') else '|-'
    body = '\n'.join(pad + line if line else '' for line in value.rstrip('\n').split('\n'))
    return f'{header}\n{body}'


def dump_yaml_data(value, indent=0):
    """Serialise dicts/lists/scalars in the subset the cards use."""
    pad = ' ' * indent

    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                if item:
                    lines.append(f'{pad}{key}:')
                    lines.append(dump_yaml_data(item, indent + 2))
                else:
                    lines.append(f'{pad}{key}: ' + ('{}' if isinstance(item, dict) else '[]'))
            elif isinstance(item, str) and '\n' in item:
                lines.append(f'{pad}{key}: {_block_scalar(item, indent)}')
            else:
                lines.append(f'{pad}{key}: {_scalar(item)}')
        return '\n'.join(lines)

    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                for pos, (key, sub) in enumerate(item.items()):
                    prefix = '- ' if pos == 0 else '  '
                    lines.append(f'{pad}{prefix}{key}: {_scalar(sub)}')
            else:
                lines.append(f'{pad}- {_scalar(item)}')
        return '\n'.join(lines)

    return f'{pad}{_scalar(value)}'


def build_document(data, body=''):
    """Reassemble the full markdown file (front matter + body)."""
    return f'---\n{dump_yaml_data(data)}\n---\n\n{body.strip()}\n'
