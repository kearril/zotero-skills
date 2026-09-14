#!/usr/bin/env python3
from __future__ import annotations

import argparse
import urllib.parse
from typing import Any

from zotero_client import (
    ZoteroClient,
    ZoteroError,
    add_common_arguments,
    batch_successful,
    client_from_args,
    item_data,
    parse_assignments,
    read_json_file,
    run_cli,
)


def make_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Plan and apply safe Zotero organization changes")
    add_common_arguments(root)
    sub = root.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="show item diff without writing")
    add_common_arguments(plan, subparser=True)
    add_item_change_arguments(plan)

    apply = sub.add_parser("apply", help="apply item diff with optimistic locking")
    add_common_arguments(apply, subparser=True)
    add_item_change_arguments(apply)
    apply.add_argument("--version", type=int, required=True)

    collections = sub.add_parser("collections", help="list collections")
    add_common_arguments(collections, subparser=True)

    create_collection = sub.add_parser("create-collection", help="create one collection")
    add_common_arguments(create_collection, subparser=True)
    create_collection.add_argument("name")
    create_collection.add_argument("--parent-key", "--parent", dest="parent_key")
    create_collection.add_argument("--apply", action="store_true")
    return root


def add_item_change_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("key", nargs="?", help="item key")
    parser.add_argument("--key", "--item-key", dest="key_opt", help="item key (alias)")
    parser.add_argument("--add-tag", action="append", default=[])
    parser.add_argument("--remove-tag", action="append", default=[])
    parser.add_argument("--add-collection", action="append", default=[])
    parser.add_argument("--remove-collection", action="append", default=[])
    parser.add_argument("--field", action="append", default=[], metavar="FIELD=VALUE")
    parser.add_argument("--relations-file")
    parser.add_argument("--parent-item")


def _tag_name(tag: Any) -> str:
    return str(tag.get("tag", "")) if isinstance(tag, dict) else str(tag)


def _schema_fields(client: ZoteroClient) -> set[str]:
    response = client.schema()
    schema = response.data if isinstance(response.data, dict) else {}
    values = schema.get("fields", schema.get("itemFields", []))
    fields: set[str] = set()
    if isinstance(values, list):
        for value in values:
            if isinstance(value, str):
                fields.add(value)
            elif isinstance(value, dict):
                name = value.get("field") or value.get("fieldName") or value.get("name")
                if name:
                    fields.add(str(name))
    return fields


def build_patch(client: ZoteroClient, item: Any, args: argparse.Namespace) -> dict[str, Any]:
    data = item_data(item)
    patch: dict[str, Any] = {}
    current_tags = list(data.get("tags", [])) if isinstance(data.get("tags", []), list) else []
    remove_tags = set(args.remove_tag)
    next_tags = [tag for tag in current_tags if _tag_name(tag) not in remove_tags]
    next_tag_names = {_tag_name(tag) for tag in next_tags}
    for tag in args.add_tag:
        if tag not in next_tag_names:
            next_tags.append({"tag": tag})
            next_tag_names.add(tag)
    if next_tags != current_tags:
        patch["tags"] = next_tags

    current_collections = list(data.get("collections", [])) if isinstance(data.get("collections", []), list) else []
    next_collections = [key for key in current_collections if key not in set(args.remove_collection)]
    for key in args.add_collection:
        if key not in next_collections:
            next_collections.append(key)
    if next_collections != current_collections:
        patch["collections"] = next_collections

    assignments = parse_assignments(args.field)
    if assignments:
        known_fields = _schema_fields(client)
        unknown = sorted(set(assignments) - known_fields) if known_fields else []
        if unknown:
            raise ValueError(f"fields are not present in Zotero schema: {', '.join(unknown)}")
        for field, value in assignments.items():
            if data.get(field, "") != value:
                patch[field] = value

    if args.relations_file:
        relations = read_json_file(args.relations_file)
        if not isinstance(relations, dict):
            raise ValueError("--relations-file must contain a JSON object")
        if data.get("relations", {}) != relations:
            patch["relations"] = relations
    if args.parent_item is not None and data.get("parentItem") != args.parent_item:
        patch["parentItem"] = args.parent_item
    return patch


def _resolve_key(args: argparse.Namespace) -> str:
    key = getattr(args, "key", None) or getattr(args, "key_opt", None)
    if not key:
        raise ValueError("item key is required (pass as positional argument or --key)")
    return str(key).strip()


def diff_for(client: ZoteroClient, args: argparse.Namespace) -> dict[str, Any]:
    target_key = _resolve_key(args)
    response = client.item(target_key)
    item = response.data
    patch = build_patch(client, item, args)
    current = item_data(item)
    before = {field: current.get(field) for field in patch}
    return {
        "item_key": target_key,
        "version": item.get("version", current.get("version")),
        "changed": bool(patch),
        "before": before,
        "after": patch,
        "patch": patch,
    }


def do_plan(args: argparse.Namespace) -> dict[str, Any]:
    return diff_for(client_from_args(args), args)


def do_apply(args: argparse.Namespace) -> dict[str, Any]:
    client = client_from_args(args)
    target_key = _resolve_key(args)
    diff = diff_for(client, args)
    current_version = diff.get("version")
    if current_version != args.version:
        raise ZoteroError(
            f"planned version {args.version} differs from current version {current_version}",
            code="VERSION_CONFLICT",
            status=412,
        )
    if not diff["changed"]:
        return {"item_key": target_key, "changed": False, "version": current_version, "verified": True}
    response = client.patch_item(target_key, diff["patch"], version=args.version)
    updated = client.item(target_key).data
    updated_data = item_data(updated)
    verified = all(updated_data.get(field) == value for field, value in diff["patch"].items())
    if not verified:
        raise ZoteroError("item after patch does not contain requested values", code="VERIFY_FAILED")
    return {
        "item_key": target_key,
        "changed": True,
        "version": updated.get("version"),
        "response": response.data,
        "verified": True,
        "item": updated,
    }

def do_collections(args: argparse.Namespace) -> dict[str, Any]:
    client = client_from_args(args)
    response = client.library_get("collections")
    return {"collections": response.data if isinstance(response.data, list) else []}


def do_create_collection(args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {"name": args.name}
    if args.parent_key:
        body["parentCollection"] = args.parent_key
    if not args.apply:
        return {"apply": False, "collection": body}
    client = client_from_args(args)
    response = client.library_write("POST", "collections", body=[body])
    result = response.data
    entry = batch_successful(result).get("0", {})
    key = entry.get("key")
    if not key:
        raise ZoteroError("created collection key missing from batch response", code="BATCH_PARTIAL", details=result)
    created = client.library_get(f"collections/{urllib.parse.quote(str(key), safe='')}").data
    created_data = created.get("data", {}) if isinstance(created, dict) else {}
    verified = created_data.get("name") == args.name and (
        not args.parent_key or created_data.get("parentCollection") == args.parent_key
    )
    if not verified:
        raise ZoteroError("created collection failed read-back verification", code="VERIFY_FAILED")
    return {"apply": True, "response": result, "collection": created, "verified": True}


def main() -> int:
    args = make_parser().parse_args()
    actions = {
        "plan": do_plan,
        "apply": do_apply,
        "collections": do_collections,
        "create-collection": do_create_collection,
    }
    return run_cli(args.command, lambda: actions[args.command](args))


if __name__ == "__main__":
    raise SystemExit(main())
