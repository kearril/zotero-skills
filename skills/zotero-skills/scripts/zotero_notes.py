#!/usr/bin/env python3
from __future__ import annotations

import argparse
import urllib.parse

from zotero_client import (
    ZoteroError,
    add_common_arguments,
    batch_successful,
    client_from_args,
    html_note,
    item_data,
    read_text_input,
    run_cli,
)


def make_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Read and write Zotero notes and indexed text")
    add_common_arguments(root)
    sub = root.add_subparsers(dest="command", required=True)

    listing = sub.add_parser("list", help="list child notes or annotations")
    add_common_arguments(listing, subparser=True)
    listing.add_argument("parent_key", nargs="?", help="parent item key")
    listing.add_argument("--parent", "--key", dest="parent_key_opt", help="parent item key (alias)")
    listing.add_argument("--kind", choices=("note", "annotation", "all"), default="all")

    get = sub.add_parser("get", help="read one note or annotation")
    add_common_arguments(get, subparser=True)
    get.add_argument("key", nargs="?", help="note or annotation key")
    get.add_argument("--key", dest="key_opt", help="note or annotation key (alias)")
    create = sub.add_parser("create", help="plan or create a note")
    add_common_arguments(create, subparser=True)
    create.add_argument("--parent", "--key", dest="parent", required=True, help="parent item key")
    create.add_argument("--title")
    create.add_argument("--body")
    create.add_argument("--file")
    create.add_argument("--stdin", action="store_true")
    create.add_argument("--tag", action="append", default=[])
    create.add_argument("--apply", action="store_true")

    update = sub.add_parser("update", help="plan or update a note")
    add_common_arguments(update, subparser=True)
    update.add_argument("key", nargs="?", help="note key")
    update.add_argument("--key", dest="key_opt", help="note key (alias)")
    update.add_argument("--file")
    update.add_argument("--body")
    update.add_argument("--stdin", action="store_true")
    update.add_argument("--version", type=int, required=True)
    update.add_argument("--apply", action="store_true")

    fulltext = sub.add_parser("write-fulltext", help="plan or write indexed full text")
    add_common_arguments(fulltext, subparser=True)
    fulltext.add_argument("key", nargs="?", help="attachment key")
    fulltext.add_argument("--key", dest="key_opt", help="attachment key (alias)")
    fulltext.add_argument("--content")
    fulltext.add_argument("--file")
    fulltext.add_argument("--stdin", action="store_true")
    fulltext.add_argument("--version", type=int, required=True)
    fulltext.add_argument("--apply", action="store_true")
    return root


def _children(client: ZoteroClient, parent_key: str) -> list:
    response = client.children(parent_key)
    return response.data if isinstance(response.data, list) else []


def _resolve_parent_key(args: argparse.Namespace) -> str:
    key = getattr(args, "parent_key", None) or getattr(args, "parent_key_opt", None)
    if not key:
        raise ValueError("parent key is required (pass as positional argument or --parent/--key)")
    return str(key).strip()


def _resolve_key(args: argparse.Namespace) -> str:
    key = getattr(args, "key", None) or getattr(args, "key_opt", None)
    if not key:
        raise ValueError("key is required (pass as positional argument or --key)")
    return str(key).strip()


def do_list(args: argparse.Namespace) -> dict:
    client = client_from_args(args)
    parent_key = _resolve_parent_key(args)
    children = _children(client, parent_key)
    if args.kind != "all":
        children = [child for child in children if item_data(child).get("itemType") == args.kind]
    return {"parent_key": parent_key, "kind": args.kind, "items": children, "count": len(children)}


def do_get(args: argparse.Namespace) -> dict:
    client = client_from_args(args)
    target_key = _resolve_key(args)
    response = client.item(target_key)
    return {"item": response.data}

def note_input(args: argparse.Namespace) -> str:
    return html_note(args.title, read_text_input(text=args.body, path=args.file, stdin=args.stdin))


def create_payload(args: argparse.Namespace) -> dict:
    payload = {"itemType": "note", "parentItem": args.parent, "note": note_input(args)}
    if args.tag:
        payload["tags"] = [{"tag": tag} for tag in dict.fromkeys(args.tag)]
    return payload


def do_create(args: argparse.Namespace) -> dict:
    payload = create_payload(args)
    if not args.apply:
        return {"apply": False, "item": payload}
    client = client_from_args(args)
    response = client.create_items([payload])
    result = response.data
    entry = batch_successful(result).get("0", {})
    key = entry.get("key")
    if not key:
        raise ZoteroError("created note key missing from batch response", code="BATCH_PARTIAL", details=result)
    created = client.item(str(key)).data
    created_data = item_data(created)
    verified = created_data.get("itemType") == "note" and created_data.get("parentItem") == args.parent
    if not verified:
        raise ZoteroError("created note failed read-back verification", code="VERIFY_FAILED")
    return {"apply": True, "response": result, "item": created, "verified": True}


def do_update(args: argparse.Namespace) -> dict:
    body = read_text_input(text=args.body, path=args.file, stdin=args.stdin)
    target_key = _resolve_key(args)
    if not args.apply:
        return {"apply": False, "key": target_key, "version": args.version, "patch": {"note": body}}
    client = client_from_args(args)
    response = client.patch_item(target_key, {"note": body}, version=args.version)
    updated = client.item(target_key).data
    if item_data(updated).get("note") != body:
        raise ZoteroError("note after patch does not match requested body", code="VERIFY_FAILED")
    return {"apply": True, "key": target_key, "response": response.data, "item": updated, "verified": True}


def do_write_fulltext(args: argparse.Namespace) -> dict:
    content = read_text_input(text=args.content, path=args.file, stdin=args.stdin)
    target_key = _resolve_key(args)
    if not args.apply:
        return {"apply": False, "key": target_key, "version": args.version, "characters": len(content)}
    client = client_from_args(args)
    response = client.library_write(
        "PUT",
        f"items/{urllib.parse.quote(target_key, safe='')}/fulltext",
        body={"content": content},
        version=args.version,
    )
    verified = client.library_get(f"items/{urllib.parse.quote(target_key, safe='')}/fulltext").data
    if not isinstance(verified, dict) or verified.get("content") != content:
        raise ZoteroError("fulltext after write does not match requested content", code="VERIFY_FAILED")
    return {"apply": True, "key": target_key, "response": response.data, "verified": True}


def main() -> int:
    args = make_parser().parse_args()
    actions = {
        "list": do_list,
        "get": do_get,
        "create": do_create,
        "update": do_update,
        "write-fulltext": do_write_fulltext,
    }
    return run_cli(args.command, lambda: actions[args.command](args))


if __name__ == "__main__":
    raise SystemExit(main())
