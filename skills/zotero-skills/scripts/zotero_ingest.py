#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import urllib.parse
from pathlib import Path
from typing import Any

from zotero_client import (
    ZoteroClient,
    ZoteroError,
    add_common_arguments,
    batch_successful,
    client_from_args,
    item_data,
    md5_file,
    read_json_file,
    run_cli,
    validate_item_type,
)


def make_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Create Zotero items and upload attachments")
    add_common_arguments(root)
    sub = root.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-item", help="plan or create item metadata")
    add_common_arguments(create, subparser=True)
    create.add_argument("--type", required=True, dest="item_type")
    create.add_argument("--json-file", required=True, dest="item_file")
    create.add_argument("--apply", action="store_true")

    upload = sub.add_parser("upload", help="plan or upload attachment file")
    add_common_arguments(upload, subparser=True)
    upload.add_argument("key")
    upload.add_argument("file")
    upload.add_argument("--replace", action="store_true")
    upload.add_argument("--apply", action="store_true")
    return root


def load_items(args: argparse.Namespace, client: ZoteroClient) -> list[dict[str, Any]]:
    loaded = read_json_file(args.item_file)
    items = loaded if isinstance(loaded, list) else [loaded]
    if not items or len(items) > 50 or not all(isinstance(item, dict) for item in items):
        raise ValueError("--json-file must contain one object or an array of 1 to 50 objects")
    result: list[dict[str, Any]] = []
    for item in items:
        payload = dict(item)
        actual_type = payload.get("itemType") or args.item_type
        if actual_type != args.item_type:
            raise ValueError(f"itemType mismatch: --type={args.item_type}, payload={actual_type}")
        payload["itemType"] = actual_type
        result.append(payload)
    validate_item_type(client, args.item_type)
    return result


def do_create_item(args: argparse.Namespace) -> dict[str, Any]:
    client = client_from_args(args)
    items = load_items(args, client)
    if not args.apply:
        return {"apply": False, "items": items, "count": len(items)}
    response = client.create_items(items)
    result = response.data
    successful = batch_successful(result)
    verified_items = []
    for index, entry in successful.items():
        key = entry.get("key")
        if not key:
            continue
        created = client.item(str(key)).data
        verified_items.append({"index": index, "key": key, "item": created})
    failed = result.get("failed", {}) if isinstance(result, dict) else {}
    if failed or len(verified_items) != len(items):
        return {
            "apply": True,
            "response": result,
            "verified_items": verified_items,
            "verified": False,
            "count": len(items),
        }
    return {
        "apply": True,
        "response": result,
        "verified_items": verified_items,
        "verified": True,
        "count": len(items),
    }


def upload_plan(client: ZoteroClient, args: argparse.Namespace) -> dict[str, Any]:
    source = Path(args.file).expanduser()
    if not source.is_file():
        raise ValueError(f"attachment file does not exist: {source}")
    stat = source.stat()
    if stat.st_size >= 4 * 1024 * 1024 * 1024:
        raise ValueError("local API full upload requires a file smaller than 4 GiB")
    item = client.item(args.key).data
    data = item_data(item)
    if data.get("itemType") != "attachment":
        raise ValueError(f"item is not an attachment: {args.key}")
    if data.get("linkMode") not in ("imported_file", "imported_url"):
        raise ValueError("only imported_file or imported_url attachments support upload")
    old_md5 = data.get("md5")
    if old_md5 and not args.replace:
        raise ValueError("attachment already has a file; pass --replace for explicit replacement")
    return {
        "key": args.key,
        "source": str(source.resolve()),
        "filename": source.name,
        "filesize": stat.st_size,
        "mtime": int(stat.st_mtime * 1000),
        "md5": md5_file(source),
        "previous_md5": old_md5,
        "replace": bool(old_md5),
    }


def upload_bytes(client: ZoteroClient, upload: dict[str, Any], source: Path) -> None:
    prefix = str(upload.get("prefix", "")).encode("utf-8")
    suffix = str(upload.get("suffix", "")).encode("utf-8")
    payload = bytearray(len(prefix) + source.stat().st_size + len(suffix))
    payload[: len(prefix)] = prefix
    cursor = len(prefix)
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            payload[cursor : cursor + len(chunk)] = chunk
            cursor += len(chunk)
    payload[cursor:] = suffix
    client.request(
        "POST",
        str(upload["url"]),
        raw_body=bytes(payload),
        headers={"Content-Type": str(upload["contentType"])},
        expected=(201,),
        include_api_key=False,
        include_server_id=False,
    )


def do_upload(args: argparse.Namespace) -> dict[str, Any]:
    client = client_from_args(args)
    plan = upload_plan(client, args)
    if not args.apply:
        return {"apply": False, "upload": plan}

    form = urllib.parse.urlencode(
        {
            "md5": plan["md5"],
            "filename": plan["filename"],
            "filesize": plan["filesize"],
            "mtime": plan["mtime"],
            "params": 1,
        }
    ).encode("ascii")
    condition = {"If-Match": plan["previous_md5"]} if plan["previous_md5"] else {"If-None-Match": "*"}
    authorization = client.request(
        "POST",
        f"items/{args.key}/file",
        raw_body=form,
        headers={"Content-Type": "application/x-www-form-urlencoded", **condition},
        expected=(200,),
    )
    auth_data = authorization.data if isinstance(authorization.data, dict) else {}
    if auth_data.get("exists"):
        return {"apply": True, "upload": plan, "already_exists": True, "verified": True}
    if not auth_data.get("uploadKey") or not auth_data.get("url"):
        raise ZoteroError("upload authorization omitted uploadKey or url", code="UPLOAD_AUTH_INVALID")
    source = Path(args.file).expanduser()
    upload = dict(auth_data)
    upload_bytes(client, upload, source)
    register_form = urllib.parse.urlencode({"upload": auth_data["uploadKey"]}).encode("ascii")
    registered = client.request(
        "POST",
        f"items/{args.key}/file",
        raw_body=register_form,
        headers={"Content-Type": "application/x-www-form-urlencoded", **condition},
        expected=(204, 200),
    )
    updated = client.item(args.key).data
    verified = item_data(updated).get("md5") == plan["md5"]
    if not verified:
        raise ZoteroError("attachment md5 after upload does not match source", code="VERIFY_FAILED")
    return {
        "apply": True,
        "upload": plan,
        "registered": registered.data,
        "item": updated,
        "verified": True,
    }


def main() -> int:
    args = make_parser().parse_args()
    actions = {"create-item": do_create_item, "upload": do_upload}
    return run_cli(args.command, lambda: actions[args.command](args))


if __name__ == "__main__":
    raise SystemExit(main())
