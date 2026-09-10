#!/usr/bin/env python3
"""
Delivery ASAP hub — entry point and composition root.

    ./dashboard.py                      default settings.toml
    ./dashboard.py --port 8090
    ./dashboard.py --vault sample-vault --port 8090
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dahub import settings as settings_module
from dahub.server import run


def parse_args(argv):
    parser = argparse.ArgumentParser(description='Delivery ASAP hub dashboard.')
    parser.add_argument('--settings', help='path to a settings TOML file')
    parser.add_argument('--vault', help='vault root holding the project cards')
    parser.add_argument('--projects', help='directory of project cards (overrides --vault)')
    parser.add_argument('--plan', help='path to the delivery plan markdown file')
    parser.add_argument('--host', help='bind address (default: loopback)')
    parser.add_argument('--port', type=int, help='TCP port')
    return parser.parse_args(argv[1:])


def main(argv):
    args = parse_args(argv)

    try:
        config = settings_module.configure(
            args.settings, vault=args.vault, projects_dir=args.projects,
            plan_path=args.plan, host=args.host, port=args.port)
    except settings_module.SettingsError as exc:
        print(f'Settings error: {exc}', file=sys.stderr)
        return 2

    run(config)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
