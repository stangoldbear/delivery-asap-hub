#!/usr/bin/env python3
"""
Delivery ASAP hub — test suite (stdlib unittest, no dependencies).

    python3 -m unittest test_dahub -v      or      ./test_dahub.py

The sample vault doubles as the fixture: every case the renderer and the API
have to survive is a real card in `sample-vault/`.
"""

import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, datetime

from dahub import gantt, markup, schema, settings as settings_module, view
from dahub.api import ApiError, dispatch
from dahub.domain import (
    Timeline, format_date_long, group_by_tier, member_name, parse_gantt,
    resolve_role, tier_key,
)
from dahub.frontmatter import build_document, parse_frontmatter, parse_yaml_text
from dahub.repository import ProjectRepository, csv_to_list, write_atomic
from dahub.server import create_server

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SAMPLE_VAULT = os.path.join(REPO_ROOT, 'sample-vault')
TODAY = date(2026, 9, 9)
NOW = datetime(2026, 9, 9, 10, 30)


def sample_settings():
    return settings_module.configure(vault=SAMPLE_VAULT)


class FrontMatterTest(unittest.TestCase):
    def test_round_trip_preserves_structure(self):
        data = {
            'id': 'p1',
            'name': "Designer's name & \"brand\"",
            'tech_footprint': {'platforms': ['iOS', 'Backend (dev)'], 'content_impact': True},
            'risks_and_criticalities': [
                {'id': 'RISK-01', 'description': 'Depends on: team X', 'severity': 'high'}],
            'confluence': ['https://x.test/a', 'https://x.test/b'],
            'todos': [],
            'jira': {},
        }
        back, body = parse_frontmatter(build_document(data, 'the body'))
        self.assertEqual(back, data)
        self.assertEqual(body, 'the body')

    def test_inline_comment_is_not_part_of_the_value(self):
        """BUG-1: `tier: tier-1 # core` used to silently become tier-3."""
        data = parse_yaml_text('tier: tier-1 # tier-1 (core)\nstatus: active # or blocked\n')
        self.assertEqual(data['tier'], 'tier-1')
        self.assertEqual(data['status'], 'active')

    def test_hash_inside_a_value_survives(self):
        data = parse_yaml_text('url: https://x.test/p#frag\nname: "release #42"\n')
        self.assertEqual(data['url'], 'https://x.test/p#frag')
        self.assertEqual(data['name'], 'release #42')

    def test_block_scalars_are_read_and_written(self):
        """BUG-2: `notes: |` used to parse as the string '|', losing the body."""
        data = parse_yaml_text('notes: |-\n  first\n  second\nother: 1\n')
        self.assertEqual(data['notes'], 'first\nsecond')
        self.assertEqual(data['other'], '1')

        multiline = {'id': 'x', 'intro': 'one\ntwo "quoted"\n\nfour'}
        document = build_document(multiline)
        self.assertIn('intro: |-', document)
        self.assertEqual(parse_frontmatter(document)[0], multiline)

    def test_folded_scalar_joins_lines(self):
        self.assertEqual(parse_yaml_text('s: >-\n  a\n  b\n')['s'], 'a b')

    def test_url_in_a_list_is_not_an_inline_map(self):
        data = parse_yaml_text('confluence:\n  - https://x.test/a\n')
        self.assertEqual(data['confluence'], ['https://x.test/a'])

    def test_missing_front_matter_returns_the_body(self):
        self.assertEqual(parse_frontmatter('# just markdown'), ({}, '# just markdown'))


class SettingsTest(unittest.TestCase):
    def test_sample_settings_load(self):
        config = sample_settings()
        self.assertEqual(config.default_tier, 'tier-3')
        self.assertEqual(config.other_tier, list(config.tiers)[-1])
        self.assertIn('iOS', config.squads)

    def test_unknown_default_tier_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'bad.toml')
            with open(path, 'w') as handle:
                handle.write('[locale]\nmonths=["a","b","c","d","e","f","g","h","i","j","k","l"]\n'
                             'month_abbr=["a","b","c","d","e","f","g","h","i","j","k","l"]\n'
                             '[defaults]\ntier="nope"\n[[tiers]]\nkey="t1"\ntitle="T"\nrgb=[1,2,3]\n')
            with self.assertRaises(settings_module.SettingsError):
                settings_module.load(path)

    def test_missing_file_is_reported(self):
        with self.assertRaises(settings_module.SettingsError):
            settings_module.load('/nonexistent/settings.toml')


class VaultTestCase(unittest.TestCase):
    """Runs against a disposable copy of the sample vault."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.vault = os.path.join(self.tmp, 'vault')
        shutil.copytree(SAMPLE_VAULT, self.vault)
        self.settings = settings_module.configure(vault=self.vault)
        self.repo = ProjectRepository(settings=self.settings)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        sample_settings()


class RepositoryTest(VaultTestCase):
    def test_cards_are_ordered_by_tier_then_priority(self):
        ids = [project['id'] for project in self.repo.list_all()]
        self.assertEqual(ids[0], 'project-1-navigation-menu')
        self.assertEqual(ids[-1], 'project-11-checkout-hardening')  # unknown tier sorts last

    def test_path_traversal_is_refused(self):
        path = self.repo.path_for('../../etc/passwd')
        self.assertEqual(os.path.dirname(path), self.repo.directory)
        self.assertFalse(self.repo.exists('../../etc/passwd'))

    def test_atomic_write_leaves_no_partial_file(self):
        target = os.path.join(self.vault, 'card.md')
        write_atomic(target, 'first\n')
        with self.assertRaises(TypeError):
            write_atomic(target, None)
        with open(target) as handle:
            self.assertEqual(handle.read(), 'first\n')
        leftovers = [name for name in os.listdir(self.vault) if name.startswith('.tmp-')]
        self.assertEqual(leftovers, [])

    def test_hand_written_card_keeps_its_tier_through_a_save(self):
        """The card with inline comments must survive the parse → save cycle."""
        self.assertTrue(self.repo.mutate('project-2-eco-labels', lambda data: None))
        data, _ = self.repo.load('project-2-eco-labels')
        self.assertEqual(data['tier'], 'tier-1')
        self.assertEqual(data['status'], 'blocked')
        self.assertIn('Regulatory requirement', data['intro'])
        self.assertIn('\n', data['intro'])

    def test_write_raw_refuses_invalid_front_matter(self):
        before = self.repo.read_raw('project-1-navigation-menu')
        with self.assertRaises(ValueError):
            self.repo.write_raw('project-1-navigation-menu', 'no front matter here')
        self.assertEqual(self.repo.read_raw('project-1-navigation-menu'), before)

    def test_plan_is_read_from_the_vault(self):
        self.assertIn('gantt', self.repo.load_plan())

    def test_csv_coercion(self):
        self.assertEqual(csv_to_list('iOS, QA'), ['iOS', 'QA'])
        self.assertEqual(csv_to_list(['iOS']), ['iOS'])
        self.assertEqual(csv_to_list(''), [])


class DomainTest(unittest.TestCase):
    def setUp(self):
        self.settings = sample_settings()
        self.tasks = parse_gantt(
            ProjectRepository(settings=self.settings).load_plan(), self.settings)

    def test_date_formats(self):
        self.assertEqual(format_date_long('2026-08-24', self.settings), '24 August 26')
        self.assertEqual(format_date_long('24/08/2026', self.settings), '24 August 26')
        self.assertEqual(format_date_long('mid October', self.settings), 'mid October')
        self.assertEqual(format_date_long('', self.settings), '')

    def test_unknown_tier_falls_back_to_the_default(self):
        self.assertEqual(tier_key({'tier': 'tier-9'}, self.settings), 'tier-3')
        self.assertEqual(tier_key({}, self.settings), 'tier-3')

    def test_roles_come_from_the_roster_not_from_keywords(self):
        role, _ = resolve_role('iOS', 'iOS Dev #1 call the Server API', self.settings)
        self.assertEqual(role, 'iOS Dev')
        self.assertEqual(member_name('iOS', 'iOS Dev #1 anything', self.settings), 'Rita Levi')
        self.assertEqual(member_name('iOS', 'Contractor #7 x', self.settings), 'Resource')

    def test_gantt_modifiers_and_project_codes(self):
        by_label = {task['label']: task for task in self.tasks}
        self.assertEqual(by_label['Backend Dev #1 P1 Menu API v2']['type'], 'crit')
        self.assertEqual(by_label['QA #2 time off']['type'], 'done')
        self.assertEqual(by_label['Backend Dev #1 P1 Menu API v2']['project_id'],
                         'project-1-navigation-menu')
        self.assertIsNone(by_label['Company all-hands']['project_id'])
        self.assertIsNone(by_label['iOS Dev #9 P99 unknown project']['project_id'])

    def test_duration_counts_working_days_only(self):
        task = next(t for t in self.tasks if t['label'] == 'Backend Dev #1 P8 banner config')
        self.assertEqual(task['start'].date(), date(2026, 9, 2))
        self.assertEqual(task['end'].date(), date(2026, 9, 16))   # 10 working days

    def test_timeline_covers_past_and_future_tasks(self):
        timeline = Timeline(self.tasks, settings=self.settings, today=TODAY)
        self.assertEqual(timeline.days[0].date(), date(2026, 1, 12))
        self.assertGreaterEqual(timeline.days[-1].date(), date(2027, 3, 31))
        self.assertIsNotNone(timeline.today_index)
        self.assertTrue(all(day.weekday() < 5 for day in timeline.days))

    def test_hide_past_drops_earlier_days(self):
        timeline = Timeline(self.tasks, settings=self.settings, hide_past=True, today=TODAY)
        self.assertEqual(timeline.days[0].date(), TODAY)
        self.assertEqual(timeline.today_index, 0)

    def test_geometry_is_none_outside_the_scale(self):
        timeline = Timeline([], settings=self.settings, today=TODAY)
        far = datetime(2030, 1, 1)
        self.assertIsNone(timeline.geometry(far, far))

    def test_grouping_keeps_the_declared_tier_order(self):
        grouped = group_by_tier([{'tier': 'tier-9'}, {'tier': 'tier-1'}], self.settings)
        self.assertEqual(list(grouped), list(self.settings.tiers))
        self.assertEqual(len(grouped['tier-3']), 1)      # the unknown tier lands here


class SchemaAndApiTest(VaultTestCase):
    PROJECT = 'project-1-navigation-menu'

    def test_invalid_status_is_rejected_before_it_reaches_the_file(self):
        with self.assertRaises(ApiError) as caught:
            dispatch(self.repo, self.PROJECT, 'update', {'status': 'whatever'}, now=NOW)
        self.assertEqual(caught.exception.status, 400)
        self.assertEqual(self.repo.load(self.PROJECT)[0]['status'], 'active')

    def test_invalid_deadline_type_and_severity_are_rejected(self):
        for payload in ({'deadline_type': 'medium'},):
            with self.assertRaises(ApiError):
                dispatch(self.repo, self.PROJECT, 'update', payload, now=NOW)
        with self.assertRaises(ApiError):
            dispatch(self.repo, self.PROJECT, 'advanced-update',
                     {'risks_and_criticalities': [{'id': 'R', 'severity': 'apocalyptic'}]}, now=NOW)

    def test_quick_update_writes_only_the_fields_it_owns(self):
        before, _ = self.repo.load(self.PROJECT)
        dispatch(self.repo, self.PROJECT, 'update',
                 {'status': 'blocked', 'blocked_reason': 'waiting', 'platforms': 'iOS, QA'},
                 now=NOW)
        after, _ = self.repo.load(self.PROJECT)
        self.assertEqual(after['status'], 'blocked')
        self.assertEqual(after['tech_footprint']['platforms'], ['iOS', 'QA'])
        self.assertEqual(after['todos'], before['todos'])
        self.assertEqual(after['risks_and_criticalities'], before['risks_and_criticalities'])

    def test_advanced_update_leaves_untouched_fields_alone(self):
        before, _ = self.repo.load(self.PROJECT)
        dispatch(self.repo, self.PROJECT, 'advanced-update',
                 {'dates': {'started': '2026-08-25'}, 'body': 'replaced body'}, now=NOW)
        after, body = self.repo.load(self.PROJECT)
        self.assertEqual(after['dates']['started'], '2026-08-25')
        self.assertEqual(after['dates']['deadline_type'], before['dates']['deadline_type'])
        self.assertEqual(after['todos'], before['todos'])
        self.assertEqual(after['intro'], before['intro'])
        self.assertEqual(body, 'replaced body')

    def test_readonly_fields_cannot_be_written(self):
        dispatch(self.repo, self.PROJECT, 'advanced-update',
                 {'tier': 'tier-3', 'priority': '99'}, now=NOW)
        after, _ = self.repo.load(self.PROJECT)
        self.assertEqual(after['tier'], 'tier-1')
        self.assertEqual(after['priority'], '1')

    def test_todo_lifecycle(self):
        dispatch(self.repo, self.PROJECT, 'todo/add', {'text': 'new note'}, now=NOW)
        data, _ = self.repo.load(self.PROJECT)
        todo_id = data['todos'][-1]['id']

        dispatch(self.repo, self.PROJECT, 'todo/update',
                 {'todo_id': todo_id, 'text': 'edited', 'deadline': '2026-10-01'}, now=NOW)
        dispatch(self.repo, self.PROJECT, 'todo/toggle', {'todo_id': todo_id}, now=NOW)
        data, _ = self.repo.load(self.PROJECT)
        done = next(item for item in data['todos_history'] if item['id'] == todo_id)
        self.assertEqual(done['text'], 'edited')
        self.assertEqual(done['completed_at'], '2026-09-09 10:30')

        dispatch(self.repo, self.PROJECT, 'todo/toggle', {'todo_id': todo_id}, now=NOW)
        data, _ = self.repo.load(self.PROJECT)
        reopened = next(item for item in data['todos'] if item['id'] == todo_id)
        self.assertNotIn('completed_at', reopened)

        dispatch(self.repo, self.PROJECT, 'todo/delete', {'todo_id': todo_id}, now=NOW)
        data, _ = self.repo.load(self.PROJECT)
        self.assertNotIn(todo_id, [item['id'] for item in data['todos']])

    def test_empty_todo_text_is_refused(self):
        with self.assertRaises(ApiError):
            dispatch(self.repo, self.PROJECT, 'todo/add', {'text': '   '}, now=NOW)

    def test_reorder_numbers_projects_inside_their_own_tier(self):
        result = dispatch(self.repo, '_batch', 'reorder', {'order': [
            {'id': 'project-3-home-redesign', 'tier': 'tier-1'},
            {'id': self.PROJECT, 'tier': 'tier-1'},
            {'id': 'project-8-banner-defaults', 'tier': 'tier-3'},
        ]}, now=NOW)
        self.assertEqual(result['updated'], 3)
        self.assertEqual(self.repo.load('project-3-home-redesign')[0]['priority'], '1')
        self.assertEqual(self.repo.load(self.PROJECT)[0]['priority'], '2')
        self.assertEqual(self.repo.load('project-8-banner-defaults')[0]['priority'], '1')

    def test_reorder_refuses_an_unknown_tier(self):
        with self.assertRaises(ApiError):
            dispatch(self.repo, '_batch', 'reorder',
                     {'order': [{'id': self.PROJECT, 'tier': 'tier-42'}]}, now=NOW)

    def test_unknown_action_and_unknown_project(self):
        for project_id, action in ((self.PROJECT, 'nope'), ('ghost', 'update')):
            with self.assertRaises(ApiError) as caught:
                dispatch(self.repo, project_id, action, {}, now=NOW)
            self.assertEqual(caught.exception.status, 404)

    def test_raw_update_validates_before_writing(self):
        before = self.repo.read_raw(self.PROJECT)
        with self.assertRaises(ApiError):
            dispatch(self.repo, self.PROJECT, 'raw-update', {'raw_text': 'broken'}, now=NOW)
        self.assertEqual(self.repo.read_raw(self.PROJECT), before)

        dispatch(self.repo, self.PROJECT, 'raw-update',
                 {'raw_text': '---\nid: "%s"\nname: "Renamed"\n---\n\nbody\n' % self.PROJECT},
                 now=NOW)
        self.assertEqual(self.repo.load(self.PROJECT)[0]['name'], 'Renamed')


class ViewTest(unittest.TestCase):
    def setUp(self):
        self.settings = sample_settings()
        self.repo = ProjectRepository(settings=self.settings)
        self.projects = self.repo.list_all()
        self.tasks = parse_gantt(self.repo.load_plan(), self.settings)
        self.html = view.render_page(self.projects, self.tasks, today=TODAY,
                                     settings=self.settings)

    def test_page_renders_every_tier_and_project(self):
        for project in self.projects:
            self.assertIn(f'data-proj-id="{project["id"]}"', self.html)
        self.assertIn('TIER 1 — CORE &amp; COMPLIANCE', self.html)
        self.assertIn('OPERATIONAL &amp; TEAM TIME OFF', self.html)

    def test_special_characters_are_escaped(self):
        self.assertIn('Designer&#x27;s name &amp; brand page &quot;phase 2&quot;', self.html)
        self.assertNotIn('Designer\'s name & brand page "phase 2"', self.html)

    def test_link_counts_match_the_stored_values(self):
        """An empty section used to claim `(1)` because of its placeholder row."""
        card = next(p for p in self.projects if p['id'] == 'project-6-designer-name')
        detail = view.render_detail_row(card, 'tier-2', self.settings)
        self.assertIn('<span>Confluence (0):</span>', detail)
        self.assertIn('<span>Epics (1):</span>', detail)

    def test_unknown_status_is_not_silently_replaced(self):
        card = next(p for p in self.projects if p['id'] == 'project-11-checkout-hardening')
        detail = view.render_detail_row(card, 'tier-3', self.settings)
        self.assertIn('on-hold (invalid)', detail)

    def test_dangerous_link_schemes_are_dropped(self):
        card = {'id': 'x', 'confluence': ['javascript:alert(1)']}
        detail = view.render_detail_row(card, 'tier-1', self.settings)
        self.assertNotIn('href="javascript:', detail)
        self.assertNotIn('\U0001F517 OPEN', detail)                 # no link button at all
        self.assertIn('value="javascript:alert(1)"', detail)   # kept as text, not as a link

    def test_project_without_tasks_has_a_disabled_caret(self):
        chart = gantt.render(self.projects, self.tasks,
                             Timeline(self.tasks, settings=self.settings, today=TODAY),
                             detail_row=lambda project, tier: '', settings=self.settings)
        self.assertIn('id="btn-toggle-proj-project-7-menu-endpoint" '
                      'data-action="toggle-project" data-project="project-7-menu-endpoint" '
                      'disabled', chart)

    def test_layout_metrics_travel_as_css_variables(self):
        self.assertIn('--label-w:340px', self.html)
        self.assertIn('--col-w:17px', self.html)
        self.assertNotIn('http://', self.html.split('<body>')[0])   # no external asset

    def test_markup_helpers(self):
        self.assertEqual(markup.ensure_list('a,b'), ['a,b'])        # never splits
        self.assertEqual(markup.safe_url('javascript:x'), '')
        self.assertEqual(markup.safe_url('https://x.test'), 'https://x.test')


class ServerTest(VaultTestCase):
    def setUp(self):
        super().setUp()
        self.settings = settings_module.configure(vault=self.vault, host='127.0.0.1', port=0)
        self.repo = ProjectRepository(settings=self.settings)
        self.httpd = create_server(self.settings, self.repo)
        self.base = 'http://127.0.0.1:%d' % self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        super().tearDown()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=5) as response:
            return response.status, response.read().decode('utf-8'), dict(response.headers)

    def post(self, path, payload):
        request = urllib.request.Request(
            self.base + path, data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_dashboard_renders(self):
        status, body, headers = self.get('/')
        self.assertEqual(status, 200)
        self.assertIn('Delivery ASAP hub', body)
        self.assertIn('project-1-navigation-menu', body)
        self.assertIn("default-src 'self'", headers['Content-Security-Policy'])

    def test_hide_past_query_switches_the_toggle(self):
        self.assertIn('Show all dates', self.get('/?hide_past=1')[1])
        self.assertIn('Show from today', self.get('/')[1])

    def test_health_and_schema_endpoints(self):
        self.assertEqual(json.loads(self.get('/api/health')[1])['status'], 'ok')
        payload = json.loads(self.get('/api/schema')[1])
        self.assertTrue(payload['success'])
        self.assertEqual([section['key'] for section in payload['sections']][0], 'general')

    def test_raw_endpoint_returns_data_body_and_text(self):
        payload = json.loads(self.get('/api/project/project-1-navigation-menu/raw')[1])
        self.assertEqual(payload['data']['id'], 'project-1-navigation-menu')
        self.assertIn('Phase 1', payload['body'])
        self.assertTrue(payload['raw_text'].startswith('---'))

    def test_static_assets_are_served_and_traversal_is_blocked(self):
        self.assertIn('Delivery ASAP hub', self.get('/static/app.css')[1])
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.get('/static/../../settings.toml')
        self.assertEqual(caught.exception.code, 404)

    def test_post_update_round_trip(self):
        status, payload = self.post('/api/project/project-8-banner-defaults/update',
                                    {'status': 'blocked', 'blocked_reason': 'vendor'})
        self.assertEqual((status, payload['success']), (200, True))
        self.assertEqual(self.repo.load('project-8-banner-defaults')[0]['status'], 'blocked')

    def test_post_invalid_payload_is_rejected_with_a_message(self):
        status, payload = self.post('/api/project/project-8-banner-defaults/update',
                                    {'status': 'nope'})
        self.assertEqual(status, 400)
        self.assertIn('Allowed', payload['error'])

    def test_unknown_endpoint(self):
        self.assertEqual(self.post('/api/nope', {})[0], 404)


if __name__ == '__main__':
    unittest.main(verbosity=2)
