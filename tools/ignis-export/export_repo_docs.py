#!/usr/bin/env python3
"""Export selected repository Markdown to an owned Ignis vault subtree.

Security contract: the client pins the CA bundle shipped beside this file,
asserts the peer SHA-256 fingerprint before every run, uses SNI ignis.local,
and never disables certificate verification. Credentials are optional and only
read from IGNIS_BEARER_TOKEN at runtime; they are never saved in state or logs.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import socket
import ssl
import sys
import time
from pathlib import Path, PurePosixPath
from urllib.parse import urlencode

HOST = "ignis.local"
IP = "172.16.40.65"
PORT = 443
VAULT = "My Vault"
FINGERPRINT = "5E:2C:E9:1D:CA:ED:B4:1E:52:53:83:41:83:31:F5:64:03:C1:34:64:15:36:8D:A8:11:3F:0F:50:EF:4E:FA:96"
RETRIES = 3
WIKILINK = re.compile(r"(?<!!)\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to the private IP while validating SNI hostname ignis.local."""
    def connect(self):
        raw = socket.create_connection((IP, PORT), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(raw, server_hostname=HOST)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ca_path() -> Path:
    return Path(__file__).with_name("ignis_pin.pem")


def assert_tls() -> ssl.SSLContext:
    ca = ca_path()
    if not ca.is_file():
        raise RuntimeError(f"missing pinned CA: {ca}")
    local = ssl.PEM_cert_to_DER_cert(ca.read_text())
    if ssl.DER_cert_to_PEM_cert(local) is None:  # Defensive parse check.
        raise RuntimeError("invalid pinned CA")
    local_fp = hashlib.sha256(local).hexdigest().upper()
    expected = FINGERPRINT.replace(":", "")
    if local_fp != expected:
        raise RuntimeError("pinned CA fingerprint mismatch; aborting")
    ctx = ssl.create_default_context(cafile=str(ca))
    # This handshake verifies chain and hostname; it is not a verification bypass.
    with socket.create_connection((IP, PORT), timeout=15) as raw:
        with ctx.wrap_socket(raw, server_hostname=HOST) as verified:
            peer_fp = hashlib.sha256(verified.getpeercert(binary_form=True)).hexdigest().upper()
    if peer_fp != expected:
        raise RuntimeError("server certificate fingerprint mismatch; aborting")
    return ctx


def request(ctx: ssl.SSLContext, method: str, path: str, body=None, headers=None):
    payload = None if body is None else json.dumps(body, separators=(",", ":")).encode()
    h = {"Accept": "application/json"}
    if payload is not None:
        h["Content-Type"] = "application/json"
    token = os.environ.get("IGNIS_BEARER_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    if headers:
        h.update(headers)
    last = None
    for attempt in range(RETRIES):
        try:
            conn = PinnedHTTPSConnection(HOST, PORT, context=ctx, timeout=30)
            conn.request(method, path, payload, h)
            response = conn.getresponse()
            raw = response.read()
            status = response.status
            out_headers = dict(response.getheaders())
            conn.close()
            if status in (429, 500, 502, 503, 504) and attempt + 1 < RETRIES:
                time.sleep(2 ** attempt)
                continue
            if status >= 400:
                raise RuntimeError(f"{method} {path}: HTTP {status}: {raw[:500].decode(errors='replace')}")
            if not raw:
                decoded = {}
            else:
                text = raw.decode("utf-8")
                try:
                    decoded = json.loads(text.lstrip("\ufeff").strip())
                except json.JSONDecodeError:
                    decoded = text
            return status, out_headers, decoded
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            last = exc
            if attempt + 1 < RETRIES:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"{method} {path} failed after {RETRIES} attempts: {last}")


def safe_rel(path: Path, root: Path) -> str:
    rel = path.resolve().relative_to(root.resolve())
    if any(part in ("", ".", "..") for part in rel.parts):
        raise ValueError(f"unsafe path: {path}")
    return rel.as_posix()


def markdown_sources(root: Path, requested: list[str]) -> list[Path]:
    if requested:
        files = [root / item for item in requested]
    else:
        files = [root / "README.md"] + sorted(root.glob("*/README.md"))
    result = []
    for path in files:
        if not path.is_file() or path.suffix.lower() != ".md":
            raise ValueError(f"not an exportable Markdown file: {path}")
        safe_rel(path, root)
        result.append(path)
    return result


def check_links(text: str, available_titles: set[str]) -> list[str]:
    # Links to the established vault protocol/navigation are allowed external anchors.
    allowed = {"Documentation Protocol", "Home", "Fleet Agents"}
    return sorted({name.strip() for name in WIKILINK.findall(text)
                   if name.strip() not in available_titles | allowed})


def state_file(root: Path) -> Path:
    return root / ".ignis-export-state.json"


def load_state(root: Path) -> dict:
    path = state_file(root)
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except FileNotFoundError:
        return {}


def save_state(root: Path, value: dict) -> None:
    state_file(root).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def remote_path(repo: str, rel: str) -> str:
    return str(PurePosixPath("Hermes Fleet/Operations/Repo Exports") / repo / rel)


def ensure_dirs(ctx, full_path: str) -> None:
    current = ""
    for part in PurePosixPath(full_path).parent.parts:
        current = part if not current else f"{current}/{part}"
        try:
            request(ctx, "POST", "/api/fs/mkdir", {"vault": VAULT, "path": current})
        except RuntimeError as exc:
            # The shim reports existing directories as HTTP 500/EEXIST.
            if "EEXIST" in str(exc):
                continue
            try:
                request(ctx, "POST", "/api/fs/stat", {"vault": VAULT, "path": current})
            except RuntimeError:
                raise exc


def export(root: Path, repo: str, requested: list[str], dry_run: bool) -> dict:
    ctx = assert_tls()
    _, vault_headers, vault = request(ctx, "GET", "/api/vault/info")
    if not isinstance(vault, dict):
        raise RuntimeError(f"vault info was not JSON: {vault[:200]!r}")
    if vault.get("name") != VAULT:
        raise RuntimeError(f"unexpected vault: {vault.get('name')!r}")
    state = load_state(root)
    old_etag = state.get("treeEtag")
    tree_headers = {"If-None-Match": old_etag} if old_etag else {}
    tree_status, tree_response_headers, _ = request(ctx, "GET", "/api/fs/tree?" + urlencode({"vault": VAULT}), headers=tree_headers)
    tree_etag = tree_response_headers.get("ETag") or tree_response_headers.get("Etag") or old_etag
    files = markdown_sources(root, requested)
    titles = {p.stem for p in files}
    outputs = []
    for source in files:
        rel = safe_rel(source, root)
        source_text = source.read_text(encoding="utf-8")
        bad = check_links(source_text, titles)
        if bad:
            raise RuntimeError(f"broken wikilinks in {rel}: {', '.join(bad)}")
        content = ("---\nauthor: jayis1\nsource_repo: " + repo + "\nsource_path: " + rel +
                   "\n---\n\n[[Documentation Protocol]]\n\n" + source_text)
        data = content.encode()
        target = remote_path(repo, rel)
        entry = state.get("files", {}).get(target, {})
        remote_stat = None
        try:
            _, _, remote_stat = request(ctx, "POST", "/api/fs/stat", {"vault": VAULT, "path": target})
        except RuntimeError:
            pass
        if isinstance(remote_stat, str):
            match = re.search(r"\\{.*\\}", remote_stat, flags=re.DOTALL)
            if match:
                try:
                    remote_stat = json.loads(match.group(0))
                except json.JSONDecodeError:
                    remote_stat = None
        unchanged = (entry.get("sha256") == sha256(data) and isinstance(remote_stat, dict) and
                     remote_stat.get("size") == len(data) and remote_stat.get("mtime"))
        if unchanged:
            outputs.append({"path": target, "action": "skipped", "sha256": sha256(data)})
            continue
        if dry_run:
            outputs.append({"path": target, "action": "would-write", "sha256": sha256(data)})
            continue
        ensure_dirs(ctx, target)
        _, _, written = request(ctx, "POST", "/api/fs/writeFile", {
            "vault": VAULT, "path": target, "content": content, "encoding": "utf8", "base64": False})
        _, _, read_back = request(ctx, "GET", "/api/fs/readFile?" + urlencode({"vault": VAULT, "path": target, "encoding": "utf8"}))
        returned = read_back.get("content", "") if isinstance(read_back, dict) else (read_back if isinstance(read_back, str) else "")
        returned_bytes = returned.encode()
        if returned_bytes != data or sha256(returned_bytes) != sha256(data):
            raise RuntimeError(f"publication verification failed for {target}")
        outputs.append({"path": target, "action": "written", "sha256": sha256(data),
                        "readBackSha256": sha256(returned_bytes), "byteIdentical": True,
                        "bytes": len(data), "writeResponse": written})
    if not dry_run:
        state["treeEtag"] = tree_etag
        state["files"] = {x["path"]: {"sha256": x["sha256"]} for x in outputs}
        save_state(root, state)
    return {"vault": vault, "treeStatus": tree_status, "treeEtag": tree_etag, "files": outputs}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--repo-name", required=True)
    parser.add_argument("--path", action="append", default=[], help="relative Markdown path; repeatable")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = export(Path(args.repo_root), args.repo_name, args.path, args.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
