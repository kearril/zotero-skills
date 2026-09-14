#!/usr/bin/env python3
from __future__ import annotations

import argparse
import urllib.parse

from zotero_client import (
    ZoteroClient,
    add_common_arguments,
    client_from_args,
    item_summary,
    response_meta,
    run_cli,
)


def make_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Search Zotero Local API")
    add_common_arguments(root)
    sub = root.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="search items")
    add_common_arguments(search, subparser=True)
    search.add_argument("--q", default="")
    search.add_argument("--qmode", choices=("titleCreatorYear", "everything"), default="titleCreatorYear")
    search.add_argument("--item-type", dest="item_type")
    search.add_argument("--tag", action="append", default=[])
    search.add_argument("--collection-key", "--collection", dest="collection_key")
    search.add_argument("--saved-search-key", "--saved-search", dest="saved_search_key")
    search.add_argument("--item-key", "--key", dest="item_key")
    search.add_argument("--since", type=int)
    search.add_argument("--sort")
    search.add_argument("--direction", choices=("asc", "desc"))
    search.add_argument("--include-trashed", action="store_true")
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--start", type=int, default=0)

    collections = sub.add_parser("collections", help="list collections")
    add_common_arguments(collections, subparser=True)
    collections.add_argument("--top", action="store_true")
    collections.add_argument("--parent-key", "--parent", dest="parent_key")

    searches = sub.add_parser("searches", help="list saved searches")
    add_common_arguments(searches, subparser=True)
    return root


def do_search(args: argparse.Namespace) -> dict:
    if not 1 <= args.limit <= 100:
        raise ValueError("--limit must be between 1 and 100")
    if args.start < 0:
        raise ValueError("--start must be non-negative")
    if args.collection_key and args.saved_search_key:
        raise ValueError("choose one of --collection-key and --saved-search-key")
    client = client_from_args(args)
    if args.collection_key:
        escaped = urllib.parse.quote(args.collection_key, safe="")
        suffix = f"collections/{escaped}/items"
    elif args.saved_search_key:
        escaped = urllib.parse.quote(args.saved_search_key, safe="")
        suffix = f"searches/{escaped}/items"
    else:
        suffix = "items"

    params: list[tuple[str, object]] = [
        ("q", args.q),
        ("qmode", args.qmode),
        ("limit", args.limit),
        ("start", args.start),
    ]
    for tag in args.tag:
        params.append(("tag", tag))
    for key, value in (
        ("itemType", args.item_type),
        ("itemKey", args.item_key),
        ("since", args.since),
        ("sort", args.sort),
        ("direction", args.direction),
    ):
        if value is not None:
            params.append((key, value))
    if args.include_trashed:
        params.append(("includeTrashed", 1))
    response = client.library_get(suffix, params=params)
    items = response.data if isinstance(response.data, list) else []
    return {
        "items": [item_summary(item) for item in items if isinstance(item, dict)],
        "query": {
            "q": args.q,
            "qmode": args.qmode,
            "itemType": args.item_type,
            "tags": args.tag,
            "collectionKey": args.collection_key,
            "savedSearchKey": args.saved_search_key,
        },
        "pagination": response_meta(response),
    }


def do_collections(args: argparse.Namespace) -> dict:
    client = client_from_args(args)
    if args.parent_key:
        suffix = f"collections/{urllib.parse.quote(args.parent_key, safe='')}/collections"
    elif args.top:
        suffix = "collections/top"
    else:
        suffix = "collections"
    response = client.library_get(suffix)
    return {"collections": response.data if isinstance(response.data, list) else [], "pagination": response_meta(response)}


def do_searches(args: argparse.Namespace) -> dict:
    client = client_from_args(args)
    response = client.library_get("searches")
    return {"searches": response.data if isinstance(response.data, list) else [], "pagination": response_meta(response)}


def main() -> int:
    args = make_parser().parse_args()
    actions = {
        "search": do_search,
        "collections": do_collections,
        "searches": do_searches,
    }
    return run_cli(args.command, lambda: actions[args.command](args))


if __name__ == "__main__":
    raise SystemExit(main())
