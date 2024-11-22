import argparse
import os
import sys

from svcutils.service import Config, Service

from parze.collector import WORK_PATH, collect


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', '-p', default=os.getcwd())
    subparsers = parser.add_subparsers(dest='cmd')
    collect_parser = subparsers.add_parser('collect')
    collect_parser.add_argument('--daemon', action='store_true')
    collect_parser.add_argument('--task', action='store_true')
    collect_parser.add_argument('--no-headless', action='store_true')
    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit()
    return args


def main():
    args = parse_args()
    path = os.path.realpath(os.path.expanduser(args.path))
    config = Config(
        os.path.join(path, 'user_settings.py'),
        ITEM_STORAGE_PATH=os.path.join(path, 'parzed'),
        BROWSER_ID='chrome',
    )
    if args.cmd == 'collect':
        service = Service(
            target=collect,
            args=(config,),
            work_path=WORK_PATH,
            run_delta=3600,
            force_run_delta=2 * 3600,
            min_uptime=300,
            requires_online=True,
            max_cpu_percent=10,
        )
        if args.daemon:
            service.run()
        elif args.task:
            service.run_once()
        else:
            collect(config, headless=not args.no_headless)


if __name__ == '__main__':
    main()
