#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from zotero_client import ZoteroError, add_common_arguments, client_from_args, run_cli


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Probe Zotero Desktop Local API")
    add_common_arguments(root)
    root.add_argument("--authorize", action="store_true", help="explicitly request local write authorization")
    root.add_argument("--app-name", default="Zotero Agent", help="name shown in Zotero authorization dialog")
    return root


def check(args: argparse.Namespace) -> dict:
    client = client_from_args(args)
    root = client.probe()
    schema = client.schema()
    library = None
    library_error = None
    try:
        response = client.library_get("items", params={"limit": 1})
        library = {
            "total_results": response.header("total-results"),
            "last_modified_version": response.header("last-modified-version"),
        }
    except ZoteroError as exc:
        library_error = {"code": exc.code, "message": str(exc), "status": exc.status}

    authorized = False
    authorization = None
    if args.authorize:
        response = client.authorize(args.app_name)
        authorization = response.data
        if isinstance(authorization, dict) and authorization.get("key"):
            key_file = os.environ.get("ZOTERO_API_KEY_FILE")
            if key_file:
                Path(key_file).expanduser().write_text(str(authorization["key"]) + "\n", encoding="utf-8")
                authorization = {"remember": authorization.get("remember"), "saved_to": key_file}
            else:
                authorization = {
                    "key": authorization["key"],
                    "remember": authorization.get("remember"),
                    "warning": "store key in ZOTERO_API_KEY or ZOTERO_API_KEY_FILE; never pass it as CLI argument",
                }
            authorized = True

    schema_data = schema.data if isinstance(schema.data, dict) else {}
    item_types = schema_data.get("itemTypes", [])
    result = {
        "available": True,
        "base_url": client.base_url,
        "api_version": client.api_version or root.header("zotero-api-version"),
        "schema_version": client.schema_version or root.header("zotero-schema-version"),
        "server_id": client.server_id or root.header("zotero-server-id"),
        "schema_item_types": len(item_types) if isinstance(item_types, list) else None,
        "write_key_configured": bool(client.api_key),
        "write_authorized_now": authorized,
        "library": library,
    }
    if authorization is not None:
        result["authorization"] = authorization
    if library_error is not None:
        result["library_error"] = library_error
    return result


def main() -> int:
    args = parser().parse_args()
    return run_cli("check", lambda: check(args))


if __name__ == "__main__":
    raise SystemExit(main())
