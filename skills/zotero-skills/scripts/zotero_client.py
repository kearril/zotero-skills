#!/usr/bin/env python3
"""Small standard-library client for Zotero Desktop Local API v3."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

DEFAULT_BASE_URL = "http://127.0.0.1:23119/api/"
DEFAULT_TIMEOUT = 15.0
USER_AGENT = "ZoteroAgent/1.0"

_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "AUTH_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "LIBRARY_LOCKED",
    412: "VERSION_CONFLICT",
    413: "TOO_LARGE",
    428: "PRECONDITION_REQUIRED",
    429: "RATE_LIMITED",
    501: "UNSUPPORTED",
}


class ZoteroError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "ZOTERO_ERROR",
        status: int | None = None,
        details: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.details = details
        self.headers = dict(headers or {})


@dataclass
class APIResponse:
    status: int
    headers: dict[str, str]
    data: Any
    body: bytes

    def header(self, name: str, default: str | None = None) -> str | None:
        return self.headers.get(name.lower(), default)


def _lower_headers(headers: Any) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items()}


def _decode_body(body: bytes, headers: Mapping[str, str]) -> Any:
    if not body:
        return None
    text = body.decode("utf-8", "replace")
    content_type = headers.get("content-type", "").lower()
    if "json" in content_type or text.lstrip().startswith(("{", "[")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return text


def _urlencode(params: Mapping[str, Any] | Sequence[tuple[str, Any]] | None) -> str:
    if not params:
        return ""
    pairs: list[tuple[str, Any]] = []
    source = params.items() if isinstance(params, Mapping) else params
    for key, value in source:
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            pairs.extend((key, item) for item in value if item is not None)
        else:
            pairs.append((key, value))
    return urllib.parse.urlencode(pairs)


def _error_message(data: Any, status: int) -> str:
    if isinstance(data, dict):
        for key in ("message", "error", "code"):
            value = data.get(key)
            if value:
                return str(value)
    if isinstance(data, str) and data.strip():
        return data.strip()[:500]
    return f"Zotero Local API returned HTTP {status}"


def parse_link_header(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    links: dict[str, str] = {}
    for match in re.finditer(r"<([^>]+)>\s*;\s*rel=\"?([^,;\"]+)", value):
        links[match.group(2).strip()] = match.group(1)
    return links


def response_meta(response: APIResponse) -> dict[str, Any]:
    total = response.header("total-results")
    version = response.header("last-modified-version")
    return {
        "status": response.status,
        "total_results": int(total) if total and total.isdigit() else None,
        "last_modified_version": int(version) if version and version.isdigit() else None,
        "next": parse_link_header(response.header("link")).get("next"),
    }


def _file_url_to_path(uri: str) -> Path:
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme.lower() != "file":
        raise ValueError("Zotero did not return a file:// URL")
    return Path(urllib.request.url2pathname(parsed.path))


def safe_file_path(uri: str, storage_root: str | Path | None = None) -> Path:
    path = _file_url_to_path(uri).resolve()
    root_value = storage_root or os.environ.get("ZOTERO_STORAGE_ROOT")
    if not root_value:
        raise ValueError("set ZOTERO_STORAGE_ROOT before reading a local file")
    root = Path(root_value).expanduser().resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("file URL is outside configured Zotero storage root") from exc
    return path


def item_data(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("Zotero response item is not an object")
    data = item.get("data", item)
    if not isinstance(data, dict):
        raise ValueError("Zotero response item data is not an object")
    return data


def creator_name(creator: Mapping[str, Any]) -> str:
    if creator.get("name"):
        return str(creator["name"])
    first = str(creator.get("firstName", "")).strip()
    last = str(creator.get("lastName", "")).strip()
    return " ".join(part for part in (first, last) if part)


def item_summary(item: Mapping[str, Any]) -> dict[str, Any]:
    data = item_data(item)
    date = str(data.get("date", ""))
    year_match = re.search(r"\b(?:19|20)\d{2}\b", date)
    tags = data.get("tags", [])
    tag_names = [str(tag.get("tag", "")) if isinstance(tag, dict) else str(tag) for tag in tags]
    key = item.get("key", data.get("key"))
    return {
        "key": key,
        "version": item.get("version", data.get("version")),
        "itemType": data.get("itemType"),
        "title": data.get("title", ""),
        "creators": [creator_name(c) for c in data.get("creators", []) if isinstance(c, dict)],
        "year": year_match.group(0) if year_match else None,
        "tags": [tag for tag in tag_names if tag],
        "collections": list(data.get("collections", [])),
        "numChildren": item.get("meta", {}).get("numChildren") if isinstance(item.get("meta"), dict) else None,
        "zotero_uri": f"zotero://select/library/items/{key}" if key else None,
    }


def parse_keys(value: str, *, maximum: int = 50) -> list[str]:
    keys = [part.strip() for part in value.split(",") if part.strip()]
    if not keys:
        raise ValueError("at least one item key is required")
    if len(keys) > maximum:
        raise ValueError(f"at most {maximum} item keys are allowed")
    for key in keys:
        if not re.fullmatch(r"[A-Za-z0-9]{1,64}", key):
            raise ValueError(f"invalid Zotero key: {key}")
    return keys


def parse_assignments(values: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"expected FIELD=VALUE, got: {value}")
        field, field_value = value.split("=", 1)
        field = field.strip()
        if not field:
            raise ValueError(f"empty field in assignment: {value}")
        result[field] = field_value
    return result


def read_json_file(path: str | Path) -> Any:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_text_input(*, text: str | None = None, path: str | None = None, stdin: bool = False) -> str:
    choices = sum(value is not None for value in (text, path)) + int(stdin)
    if choices != 1:
        raise ValueError("choose exactly one of --text, --file, or --stdin")
    if text is not None:
        return text
    if path is not None:
        return Path(path).expanduser().read_text(encoding="utf-8")
    return sys.stdin.read()


def build_result(command: str, data: Any = None, **meta: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"ok": True, "command": command, "data": data}
    result.update({key: value for key, value in meta.items() if value is not None})
    return result


def build_error(command: str, error: ZoteroError | Exception) -> dict[str, Any]:
    if isinstance(error, ZoteroError):
        payload: dict[str, Any] = {
            "code": error.code,
            "message": str(error),
        }
        if error.status is not None:
            payload["status"] = error.status
        if error.details is not None:
            payload["details"] = error.details
        retry_after = error.headers.get("retry-after")
        if retry_after:
            payload["retry_after"] = retry_after
    else:
        payload = {"code": "INPUT_ERROR", "message": str(error)}
    return {"ok": False, "command": command, "error": payload}


def run_cli(command: str, action: Callable[[], Any]) -> int:
    try:
        result = build_result(command, action())
        code = 0
    except (ZoteroError, ValueError, OSError, json.JSONDecodeError) as exc:
        result = build_error(command, exc)
        code = 1
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return code


def add_common_arguments(parser: argparse.ArgumentParser, *, subparser: bool = False) -> None:
    default = argparse.SUPPRESS if subparser else None
    parser.add_argument("--base-url", default=default, help="Zotero Local API base URL")
    parser.add_argument("--library", default=default, help="users/0 or groups/<id>")
    parser.add_argument("--timeout", type=float, default=default, help="HTTP timeout in seconds")
    parser.add_argument("--json", action="store_true", default=default, help="emit machine-readable JSON")


class ZoteroClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        library: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("ZOTERO_BASE_URL") or DEFAULT_BASE_URL).rstrip("/") + "/"
        self.api_key = api_key or self._load_api_key()
        self.timeout = timeout or float(os.environ.get("ZOTERO_TIMEOUT", DEFAULT_TIMEOUT))
        self.library = self.library_path(library or os.environ.get("ZOTERO_LIBRARY", "users/0"))
        self.server_id: str | None = None
        self.api_version: str | None = None
        self.schema_version: str | None = None
        self.identity_changed = False
        self._item_types: set[str] | None = None

    @staticmethod
    def _load_api_key() -> str | None:
        value = os.environ.get("ZOTERO_API_KEY")
        if value:
            return value.strip()
        key_file = os.environ.get("ZOTERO_API_KEY_FILE")
        if key_file:
            try:
                value = Path(key_file).expanduser().read_text(encoding="utf-8").strip()
            except OSError:
                return None
            return value or None
        return None

    @staticmethod
    def library_path(value: str) -> str:
        path = value.strip().strip("/")
        if path.startswith("api/"):
            path = path[4:]
        if re.fullmatch(r"(?:users/\d+|groups/\d+)", path):
            return path
        if path.isdigit():
            return f"users/{path}"
        raise ValueError("library must be users/<id> or groups/<id>")

    def _make_url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        if path.startswith("/"):
            return urllib.parse.urljoin(self.base_url, path)
        return urllib.parse.urljoin(self.base_url, path.lstrip("/"))

    def _record_headers(self, headers: Mapping[str, str]) -> None:
        server_id = headers.get("zotero-server-id")
        if server_id:
            if self.server_id and self.server_id != server_id:
                self.api_key = None
                self.identity_changed = True
            self.server_id = server_id
        self.api_version = headers.get("zotero-api-version", self.api_version)
        self.schema_version = headers.get("zotero-schema-version", self.schema_version)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | Sequence[tuple[str, Any]] | None = None,
        body: Any = None,
        raw_body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        expected: Sequence[int] = (200,),
        include_api_key: bool = True,
        include_server_id: bool = True,
    ) -> APIResponse:
        url = self._make_url(path)
        query = _urlencode(params)
        if query:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{query}"
        request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if include_server_id and self.server_id:
            request_headers["Zotero-Server-ID"] = self.server_id
        if include_api_key and self.api_key:
            request_headers["Zotero-API-Key"] = self.api_key
        request_headers.update(headers or {})
        payload = raw_body
        if payload is None and body is not None:
            if isinstance(body, bytes):
                payload = body
            elif isinstance(body, str):
                payload = body.encode("utf-8")
            else:
                payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if payload is not None and "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=payload, headers=request_headers, method=method.upper())
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status = int(response.status)
                response_headers = _lower_headers(response.headers)
                response_body = response.read()
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            response_headers = _lower_headers(exc.headers)
            response_body = exc.read()
            self._record_headers(response_headers)
            data = _decode_body(response_body, response_headers)
            if status in expected:
                return APIResponse(status, response_headers, data, response_body)
            code = _STATUS_CODES.get(status, f"HTTP_{status}")
            raise ZoteroError(
                _error_message(data, status),
                code=code,
                status=status,
                details=data,
                headers=response_headers,
            ) from exc
        except urllib.error.URLError as exc:
            raise ZoteroError(
                f"cannot reach Zotero Local API: {exc.reason}",
                code="UNAVAILABLE",
            ) from exc
        except TimeoutError as exc:
            raise ZoteroError("Zotero Local API request timed out", code="TIMEOUT") from exc
        self._record_headers(response_headers)
        data = _decode_body(response_body, response_headers)
        if status not in expected:
            code = _STATUS_CODES.get(status, f"HTTP_{status}")
            raise ZoteroError(
                _error_message(data, status),
                code=code,
                status=status,
                details=data,
                headers=response_headers,
            )
        return APIResponse(status, response_headers, data, response_body)

    def probe(self) -> APIResponse:
        return self.request("GET", "", expected=(200,))

    def ensure_identity(self) -> None:
        if not self.server_id:
            self.probe()
        if not self.server_id:
            raise ZoteroError("Zotero response omitted Zotero-Server-ID", code="IDENTITY_MISSING")
        if self.identity_changed:
            raise ZoteroError(
                "Zotero-Server-ID changed; refresh object and authorize again",
                code="IDENTITY_CHANGED",
            )

    def write_request(
        self,
        method: str,
        path: str,
        *,
        body: Any = None,
        version: int | None = None,
        headers: Mapping[str, str] | None = None,
        expected: Sequence[int] = (200, 201, 204),
    ) -> APIResponse:
        self.ensure_identity()
        request_headers = dict(headers or {})
        if version is not None:
            request_headers["If-Unmodified-Since-Version"] = str(version)
        return self.request(method, path, body=body, headers=request_headers, expected=expected)

    def authorize(self, app_name: str = "Zotero Agent") -> APIResponse:
        self.ensure_identity()
        return self.request(
            "POST",
            "local/authorize",
            body={"appName": app_name},
            expected=(200,),
            include_api_key=False,
        )

    def get(self, path: str, *, params: Mapping[str, Any] | Sequence[tuple[str, Any]] | None = None) -> APIResponse:
        return self.request("GET", path, params=params, expected=(200,))

    def library_get(
        self,
        suffix: str = "",
        *,
        params: Mapping[str, Any] | Sequence[tuple[str, Any]] | None = None,
    ) -> APIResponse:
        path = f"{self.library}/{suffix.lstrip('/')}" if suffix else self.library
        return self.get(path, params=params)

    def library_write(
        self,
        method: str,
        suffix: str,
        *,
        body: Any = None,
        version: int | None = None,
        params: Mapping[str, Any] | Sequence[tuple[str, Any]] | None = None,
        headers: Mapping[str, str] | None = None,
        expected: Sequence[int] = (200, 201, 204),
    ) -> APIResponse:
        path = f"{self.library}/{suffix.lstrip('/')}" if suffix else self.library
        if params:
            query = _urlencode(params)
            path = f"{path}?{query}"
        return self.write_request(method, path, body=body, version=version, headers=headers, expected=expected)

    def schema(self) -> APIResponse:
        return self.get("schema")

    def item(self, key: str) -> APIResponse:
        return self.library_get(f"items/{key}")

    def children(self, key: str) -> APIResponse:
        return self.library_get(f"items/{key}/children")

    def patch_item(self, key: str, patch: Mapping[str, Any], *, version: int) -> APIResponse:
        return self.library_write("PATCH", f"items/{key}", body=dict(patch), version=version)

    def create_items(self, items: Sequence[Mapping[str, Any]]) -> APIResponse:
        if not items or len(items) > 50:
            raise ValueError("create accepts 1 to 50 items")
        return self.library_write("POST", "items", body=list(items))

    def batch_result(self, response: APIResponse) -> dict[str, Any]:
        if isinstance(response.data, dict):
            return response.data
        raise ValueError("Zotero batch response is not JSON object")


def batch_successful(data: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(data, dict) or not isinstance(data.get("successful"), dict):
        raise ValueError("Zotero response has no successful batch results")
    entries: dict[str, dict[str, Any]] = {}
    for index, value in data["successful"].items():
        if isinstance(value, dict):
            entries[str(index)] = value
    return entries


def validate_item_type(client: ZoteroClient, item_type: str) -> None:
    if client._item_types is None:
        response = client.schema()
        schema = response.data if isinstance(response.data, dict) else {}
        types = schema.get("itemTypes", [])
        known: set[str] = set()
        for value in types if isinstance(types, list) else []:
            if isinstance(value, str):
                known.add(value)
            elif isinstance(value, dict):
                candidate = value.get("itemType") or value.get("type")
                if candidate:
                    known.add(str(candidate))
        client._item_types = known
    if client._item_types and item_type not in client._item_types:
        raise ValueError(f"itemType is not present in Zotero schema: {item_type}")


def md5_file(path: str | Path) -> str:
    digest = hashlib.md5()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def html_note(title: str | None, body: str) -> str:
    if not title:
        return body
    return f"<h1>{html.escape(title)}</h1>\n{body}"


def client_from_args(args: argparse.Namespace) -> ZoteroClient:
    return ZoteroClient(
        base_url=getattr(args, "base_url", None),
        timeout=getattr(args, "timeout", None),
        library=getattr(args, "library", None),
    )
