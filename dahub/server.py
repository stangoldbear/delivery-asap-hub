"""
HTTP layer: routing, static assets, JSON serialisation.

No domain logic and no markup here — it only wires repository, domain and
view together.
"""

import json
import mimetypes
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import schema, settings as settings_module, view
from .api import ApiError, dispatch
from .domain import parse_gantt
from .repository import ProjectRepository

_API_PATH_RE = re.compile(r'^/api/project/([^/]+)/(.+)$')
_MAX_BODY_BYTES = 1 << 20  # 1 MB

# The page carries one inline <style> block with the layout custom properties;
# everything else is same-origin, so no external request ever leaves the host.
_SECURITY_HEADERS = {
    'Content-Security-Policy': (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"),
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
}


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = 'DeliveryAsapHub/1.0'
    repository = None            # injected by create_server

    # ─── GET ─────────────────────────────────────────────────────────────────
    def do_GET(self):
        path, query = self._split_path()

        if path == '/':
            return self._send_html(self._render_dashboard(query.get('hide_past') == '1'))
        if path == '/api/health':
            return self._send_json({'success': True, 'status': 'ok'})
        if path == '/api/schema':
            return self._send_json({'success': True, **schema.as_json()})

        raw_match = re.match(r'^/api/project/([^/]+)/raw$', path)
        if raw_match:
            return self._send_project_raw(raw_match.group(1))
        if path.startswith('/static/'):
            return self._send_static(path[len('/static/'):])

        self._send_error_page(404, 'Not found')

    # ─── POST ────────────────────────────────────────────────────────────────
    def do_POST(self):
        path, _ = self._split_path()
        match = _API_PATH_RE.match(path)
        if not match:
            return self._send_json({'success': False, 'error': 'Unknown endpoint'}, 404)

        project_id, action = match.group(1), match.group(2).strip('/')
        try:
            payload = dispatch(self.repository, project_id, action, self._read_json_body())
        except ApiError as exc:
            return self._send_json({'success': False, 'error': str(exc)}, exc.status)
        except Exception as exc:                      # noqa: BLE001 - API surface
            self.log_error('Internal error on %s: %s', self.path, exc)
            return self._send_json({'success': False, 'error': 'Internal server error'}, 500)

        self._send_json(payload)

    # ─── Response building ───────────────────────────────────────────────────
    def _split_path(self):
        path, _, raw_query = self.path.partition('?')
        query = {}
        for pair in raw_query.split('&'):
            if '=' in pair:
                key, _, value = pair.partition('=')
                query[key] = value
        return path, query

    def _render_dashboard(self, hide_past):
        projects = self.repository.list_all()
        tasks = parse_gantt(self.repository.load_plan())
        return view.render_page(projects, tasks, hide_past=hide_past)

    def _send_project_raw(self, project_id):
        data, body = self.repository.load(project_id)
        if data is None:
            return self._send_json({'success': False, 'error': 'Project not found'}, 404)
        return self._send_json({
            'success': True,
            'data': data,
            'body': body,
            'raw_text': self.repository.read_raw(project_id),
        })

    def _read_json_body(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
        except (TypeError, ValueError):
            raise ApiError('Invalid Content-Length header.')

        if length <= 0:
            return {}
        if length > _MAX_BODY_BYTES:
            raise ApiError('Payload too large.', status=413)

        try:
            return json.loads(self.rfile.read(length).decode('utf-8')) or {}
        except (ValueError, UnicodeDecodeError):
            raise ApiError('Request body is not valid JSON.')

    def _send_static(self, relative_path):
        static_dir = settings_module.STATIC_DIR
        target = os.path.normpath(os.path.join(static_dir, relative_path))
        # Refuse anything that escapes static/.
        if not target.startswith(static_dir + os.sep) or not os.path.isfile(target):
            return self._send_error_page(404, 'Asset not found')

        content_type = mimetypes.guess_type(target)[0] or 'application/octet-stream'
        with open(target, 'rb') as handle:
            body = handle.read()

        self._respond(200, body, f'{content_type}; charset=utf-8',
                      extra_headers={'Cache-Control': 'no-cache'})

    def _send_html(self, markup):
        self._respond(200, markup.encode('utf-8'), 'text/html; charset=utf-8')

    def _send_json(self, payload, status=200):
        self._respond(status, json.dumps(payload).encode('utf-8'),
                      'application/json; charset=utf-8')

    def _send_error_page(self, status, message):
        body = f'<!DOCTYPE html><meta charset="utf-8"><h1>{status}</h1><p>{message}</p>'
        self._respond(status, body.encode('utf-8'), 'text/html; charset=utf-8')

    def _respond(self, status, body, content_type, extra_headers=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        for name, value in {**_SECURITY_HEADERS, **(extra_headers or {})}.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        """Silence the access log; errors still go to stderr."""


def create_server(settings=None, repository=None):
    config = settings or settings_module.current()
    handler = type('BoundDashboardHandler', (DashboardHandler,),
                   {'repository': repository or ProjectRepository(settings=config)})
    return HTTPServer((config.host, config.port), handler)


def run(settings=None):
    config = settings or settings_module.current()
    httpd = create_server(config)
    host, port = httpd.server_address[0], httpd.server_address[1]
    print(f'{config.title} listening on http://{host}:{port}')
    if not os.path.isdir(config.projects_dir):
        print(f'Warning: no project cards found in {config.projects_dir}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down.')
    finally:
        httpd.server_close()
