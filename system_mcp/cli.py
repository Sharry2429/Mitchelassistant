"""
system_mcp.cli
Top-level entry point: `system-mcp <platform> <command>`.

Routes to platform-specific CLI modules.
"""

from __future__ import annotations

import argparse
import sys

from system_mcp.core.errors import SystemMCPError

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="system-mcp",
        description="Control your own devices from the command line (Windows & Android).",
    )
    platforms = parser.add_subparsers(dest="platform", required=True)

    # We import lazily or directly register if modules are ready
    try:
        from system_mcp.android import cli as android_cli
        android_cli.register(platforms)
    except ImportError:
        pass
        
    try:
        from system_mcp.windows import cli as windows_cli
        windows_cli.register(platforms)
    except ImportError:
        pass

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if hasattr(args, 'func'):
            return args.func(args)
        else:
            parser.print_help()
            return 1
    except SystemMCPError as e:
        print(f"system-mcp: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
