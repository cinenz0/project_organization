"""Command-line entry point for the centralized file organizer."""

import sys

from organize_by_suffix import organize_by_sufix
from paths import parse_args


def main(argv=None, config_file=None):
    options = parse_args(argv, config_file=config_file)
    if options.configure_only:
        print(f"Central library saved: {options.destination}")
        return 0
    try:
        result = organize_by_sufix(
            original_directory=options.source,
            dst_directory=options.destination,
            dry_run=options.dry_run,
        )
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    for operation in result["operations"]:
        message = f"{operation['status'].upper()}: {operation['source']}"
        if operation.get("destination") is not None:
            message += f" -> {operation['destination']}"
        if operation.get("error"):
            message += f" ({operation['error']})"
        print(message)
    print(f"Summary: {result['moved']} moved, {result['planned']} planned, "
          f"{result['skipped']} skipped, {result['errors']} errors")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
