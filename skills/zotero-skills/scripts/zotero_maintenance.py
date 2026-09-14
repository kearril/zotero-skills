#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import unicodedata
import urllib.parse
from collections import defaultdict
from typing import Any

from zotero_client import add_common_arguments, client_from_args, creator_name, item_data, response_meta, run_cli


def make_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Audit and inspect Zotero library changes")
    add_common_arguments(root)
    sub = root.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit", help="report missing fields and duplicate candidates")
    add_common_arguments(audit, subparser=True)
    audit.add_argument("--q", default="")
    audit.add_argument("--item-type", default="-attachment")
    audit.add_argument("--require", action="append", default=[])
    audit.add_argument("--require-pdf", action="store_true")
    audit.add_argument("--duplicates", action="store_true")
    audit.add_argument("--since", type=int)
    audit.add_argument("--limit", type=int, default=100)

    changes = sub.add_parser("changes", help="read item or full-text changes after version")
    add_common_arguments(changes, subparser=True)
    changes.add_argument("--since", type=int, required=True)
    changes.add_argument("--kind", choices=("items", "fulltext"), default="items")
    changes.add_argument("--limit", type=int, default=100)
    return root


def _missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return not value
    return False


def _has_pdf(client: Any, key: str) -> bool:
    children = client.children(key).data
    if not isinstance(children, list):
        return False
    for child in children:
        data = item_data(child)
        if data.get("itemType") != "attachment":
            continue
        content_type = str(data.get("contentType", "")).lower()
        filename = str(data.get("filename", "")).lower()
        if content_type == "application/pdf" or filename.endswith(".pdf"):
            return True
    return False


def _duplicate_key(item: Any) -> tuple[str, str] | None:
    data = item_data(item)
    doi = str(data.get("DOI", "")).strip().lower()
    if doi:
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
        return ("doi", doi)
    title = unicodedata.normalize("NFKC", str(data.get("title", ""))).casefold()
    title = re.sub(r"[^\w]+", "", title, flags=re.UNICODE)
    if not title:
        return None
    creators = data.get("creators", [])
    first = creator_name(creators[0]).casefold() if creators and isinstance(creators[0], dict) else ""
    year_match = re.search(r"\b(?:19|20)\d{2}\b", str(data.get("date", "")))
    return ("title", "|".join((title, first, year_match.group(0) if year_match else "")))


def do_audit(args: argparse.Namespace) -> dict:
    if not 1 <= args.limit <= 500:
        raise ValueError("--limit must be between 1 and 500")
    client = client_from_args(args)
    params: list[tuple[str, object]] = [("q", args.q), ("itemType", args.item_type), ("limit", args.limit)]
    if args.since is not None:
        params.append(("since", args.since))
    response = client.library_get("items", params=params)
    items = response.data if isinstance(response.data, list) else []
    required = args.require or ["DOI", "abstractNote"]
    missing = []
    for item in items:
        data = item_data(item)
        fields = [field for field in required if _missing(data.get(field))]
        pdf_missing = args.require_pdf and not _has_pdf(client, str(item.get("key", data.get("key", ""))))
        if fields or pdf_missing:
            missing.append({"key": item.get("key"), "title": data.get("title", ""), "missing": fields + (["PDF"] if pdf_missing else [])})

    duplicate_groups: list[dict[str, Any]] = []
    if args.duplicates:
        groups: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            key = _duplicate_key(item)
            if key:
                groups[key].append({"key": item.get("key"), "title": item_data(item).get("title", "")})
        duplicate_groups = [{"match": key, "items": values} for key, values in groups.items() if len(values) > 1]
    return {
        "count": len(items),
        "required_fields": required,
        "missing": missing,
        "duplicates": duplicate_groups,
        "pagination": response_meta(response),
    }


def do_changes(args: argparse.Namespace) -> dict:
    if args.limit < 1:
        raise ValueError("--limit must be positive")
    client = client_from_args(args)
    if args.kind == "fulltext":
        response = client.library_get("fulltext", params={"since": args.since})
    else:
        response = client.library_get("items", params={"since": args.since, "limit": args.limit})
    return {"since": args.since, "kind": args.kind, "result": response.data, "pagination": response_meta(response)}


def main() -> int:
    args = make_parser().parse_args()
    actions = {"audit": do_audit, "changes": do_changes}
    return run_cli(args.command, lambda: actions[args.command](args))


if __name__ == "__main__":
    raise SystemExit(main())
