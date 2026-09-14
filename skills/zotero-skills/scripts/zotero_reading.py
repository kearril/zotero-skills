#!/usr/bin/env python3
from __future__ import annotations

import argparse
import urllib.parse

from zotero_client import (
    add_common_arguments,
    client_from_args,
    item_data,
    item_summary,
    safe_file_path,
    run_cli,
)


def make_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Read Zotero items and indexed text")
    add_common_arguments(root)
    sub = root.add_subparsers(dest="command", required=True)

    get = sub.add_parser("get", help="read item metadata and children")
    add_common_arguments(get, subparser=True)
    get.add_argument("key", nargs="?", help="item key")
    get.add_argument("--key", "--item-key", dest="key_opt", help="item key (alias)")
    get.add_argument("--raw", action="store_true", help="output full raw Zotero JSON")

    children = sub.add_parser("children", help="read child items")
    add_common_arguments(children, subparser=True)
    children.add_argument("key", nargs="?", help="item key")
    children.add_argument("--key", "--item-key", dest="key_opt", help="item key (alias)")

    fulltext = sub.add_parser("fulltext", help="read bounded full-text window")
    add_common_arguments(fulltext, subparser=True)
    fulltext.add_argument("key", nargs="?", help="attachment key")
    fulltext.add_argument("--key", "--item-key", dest="key_opt", help="attachment key (alias)")
    fulltext.add_argument("--offset", type=int, default=0)
    fulltext.add_argument("--limit", type=int, default=8000)

    path = sub.add_parser("path", help="read local file URL")
    add_common_arguments(path, subparser=True)
    path.add_argument("key", nargs="?", help="attachment key")
    path.add_argument("--key", "--item-key", dest="key_opt", help="attachment key (alias)")
    path.add_argument("--storage-root")
    return root


def _resolve_key(args: argparse.Namespace) -> str:
    key = getattr(args, "key", None) or getattr(args, "key_opt", None)
    if not key:
        raise ValueError("item key is required (pass as argument or --key)")
    return str(key).strip()


def do_get(args: argparse.Namespace) -> dict:
    client = client_from_args(args)
    target_key = _resolve_key(args)
    item_response = client.item(target_key)
    children_response = client.children(target_key)
    item = item_response.data
    children = children_response.data if isinstance(children_response.data, list) else []

    if args.raw:
        return {
            "item": item,
            "summary": item_summary(item),
            "children": children,
            "child_count": len(children),
        }

    data = item_data(item)
    key = item.get("key", data.get("key", target_key))
    child_summaries = []
    for child in children:
        c_data = item_data(child)
        c_key = child.get("key", c_data.get("key"))
        title = c_data.get("title") or c_data.get("filename")
        if not title and c_data.get("note"):
            note_text = str(c_data.get("note", "")).strip()
            title = (note_text[:60] + "...") if len(note_text) > 60 else note_text
        child_summaries.append({
            "key": c_key,
            "itemType": c_data.get("itemType"),
            "title": title or "(untitled)",
            "contentType": c_data.get("contentType"),
            "zotero_uri": f"zotero://select/library/items/{c_key}" if c_key else None,
        })

    return {
        "key": key,
        "version": item.get("version", data.get("version")),
        "summary": item_summary(item),
        "abstract": data.get("abstractNote") or "",
        "doi": data.get("DOI") or data.get("doi") or "",
        "url": data.get("url") or "",
        "children": child_summaries,
        "child_count": len(children),
        "zotero_uri": f"zotero://select/library/items/{key}" if key else None,
    }


def do_children(args: argparse.Namespace) -> dict:
    client = client_from_args(args)
    target_key = _resolve_key(args)
    response = client.children(target_key)
    children = response.data if isinstance(response.data, list) else []
    return {"parent_key": target_key, "children": children, "count": len(children)}


def do_fulltext(args: argparse.Namespace) -> dict:
    if args.offset < 0:
        raise ValueError("--offset must be non-negative")
    if not 1 <= args.limit <= 50000:
        raise ValueError("--limit must be between 1 and 50000")
    client = client_from_args(args)
    target_key = _resolve_key(args)
    response = client.library_get(f"items/{urllib.parse.quote(target_key, safe='')}/fulltext")
    payload = response.data if isinstance(response.data, dict) else {}
    content = str(payload.get("content", ""))
    chunk = content[args.offset : args.offset + args.limit]
    return {
        "attachment_key": target_key,
        "offset": args.offset,
        "length": len(chunk),
        "total_characters": len(content),
        "has_more": args.offset + len(chunk) < len(content),
        "indexed_pages": payload.get("indexedPages"),
        "total_pages": payload.get("totalPages"),
        "content": chunk,
    }


def do_path(args: argparse.Namespace) -> dict:
    client = client_from_args(args)
    target_key = _resolve_key(args)
    response = client.library_get(f"items/{urllib.parse.quote(target_key, safe='')}/file/view/url")
    file_url = str(response.data).strip()
    result = {"attachment_key": target_key, "file_url": file_url}
    try:
        result["local_path"] = str(safe_file_path(file_url, args.storage_root))
    except ValueError as exc:
        result["local_path"] = None
        result["path_warning"] = str(exc)
    return result


def main() -> int:
    args = make_parser().parse_args()
    actions = {"get": do_get, "children": do_children, "fulltext": do_fulltext, "path": do_path}
    return run_cli(args.command, lambda: actions[args.command](args))


if __name__ == "__main__":
    raise SystemExit(main())
