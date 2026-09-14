#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from zotero_client import add_common_arguments, client_from_args, parse_keys, run_cli

_FORMATS = (
    "bib",
    "bibtex",
    "biblatex",
    "csljson",
    "csv",
    "mods",
    "refer",
    "rdf_bibliontology",
    "rdf_dc",
    "rdf_zotero",
    "ris",
    "tei",
    "wikipedia",
)


def make_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Export citations from Zotero Local API")
    add_common_arguments(root)
    sub = root.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export", help="export fixed item keys")
    add_common_arguments(export, subparser=True)
    export.add_argument("--keys", "--key", dest="keys", required=True, help="comma-separated item keys")
    export.add_argument("--format", choices=_FORMATS, default="bibtex")
    export.add_argument("--include")
    export.add_argument("--style")
    export.add_argument("--locale")
    export.add_argument("--linkwrap", action="store_true")
    export.add_argument("--output-file")
    return root


def do_export(args: argparse.Namespace) -> dict:
    keys = parse_keys(args.keys)
    params: list[tuple[str, object]] = [("itemKey", ",".join(keys)), ("format", args.format)]
    for key, value in (("include", args.include), ("style", args.style), ("locale", args.locale)):
        if value:
            params.append((key, value))
    if args.linkwrap:
        params.append(("linkwrap", 1))
    client = client_from_args(args)
    response = client.library_get("items", params=params)
    content = response.data
    saved_to = None
    if args.output_file:
        output = Path(args.output_file).expanduser()
        if isinstance(content, str):
            output.write_text(content, encoding="utf-8")
        else:
            output.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        saved_to = str(output)
    result = {
        "keys": keys,
        "format": args.format,
        "style": args.style,
        "locale": args.locale,
        "count": len(keys),
        "content": content,
    }
    if saved_to:
        result["saved_to"] = saved_to
    return result


def main() -> int:
    args = make_parser().parse_args()
    actions = {"export": do_export}
    return run_cli(args.command, lambda: actions[args.command](args))


if __name__ == "__main__":
    raise SystemExit(main())
