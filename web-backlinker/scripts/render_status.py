#!/usr/bin/env python3
import argparse


def cmd_init(args):
    print(f"[WB-INIT] run={args.run} | sheet={args.sheet} | targets={args.targets} | mode={args.mode} | promoted={args.promoted}")


def cmd_row(args):
    print(
        f"[WB-ROW] run={args.run} | idx={args.idx}/{args.total} | domain={args.domain} | "
        f"type={args.site_type} | result={args.result} | route={args.route} | "
        f"reason={args.reason} | next={args.next_action}"
    )


def cmd_summary(args):
    print(
        f"[WB-SUMMARY] run={args.run} | total={args.total} | submitted={args.submitted} | "
        f"verified={args.verified} | pending_email={args.pending_email} | "
        f"needs_human={args.needs_human} | skipped={args.skipped} | failed={args.failed}"
    )


def cmd_halt(args):
    print(f"[WB-HALT] run={args.run} | reason={args.reason} | last_domain={args.last_domain} | recover={args.recover}")


def main() -> int:
    parser = argparse.ArgumentParser(description='Render fixed Web Backlinker status lines.')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('init')
    p.add_argument('--run', required=True)
    p.add_argument('--sheet', required=True)
    p.add_argument('--targets', required=True)
    p.add_argument('--mode', required=True)
    p.add_argument('--promoted', default='pending')
    p.set_defaults(func=cmd_init)

    p = sub.add_parser('row')
    p.add_argument('--run', required=True)
    p.add_argument('--idx', required=True)
    p.add_argument('--total', required=True)
    p.add_argument('--domain', required=True)
    p.add_argument('--site-type', dest='site_type', required=True)
    p.add_argument('--result', required=True)
    p.add_argument('--route', required=True)
    p.add_argument('--reason', default='-')
    p.add_argument('--next-action', dest='next_action', required=True)
    p.set_defaults(func=cmd_row)

    p = sub.add_parser('summary')
    p.add_argument('--run', required=True)
    p.add_argument('--total', required=True)
    p.add_argument('--submitted', required=True)
    p.add_argument('--verified', required=True)
    p.add_argument('--pending-email', dest='pending_email', required=True)
    p.add_argument('--needs-human', dest='needs_human', required=True)
    p.add_argument('--skipped', required=True)
    p.add_argument('--failed', required=True)
    p.set_defaults(func=cmd_summary)

    p = sub.add_parser('halt')
    p.add_argument('--run', required=True)
    p.add_argument('--reason', required=True)
    p.add_argument('--last-domain', dest='last_domain', default='-')
    p.add_argument('--recover', required=True)
    p.set_defaults(func=cmd_halt)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
