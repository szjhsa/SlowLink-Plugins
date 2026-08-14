#!/usr/bin/env python3
"""Build a SlowLink plugin release zip and its SHA256SUMS file."""

import argparse
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
DIST = ROOT / "dist"
PLUGIN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_plugin(plugin_id: str) -> dict:
    if not PLUGIN_ID_RE.fullmatch(plugin_id):
        raise ValueError(f"invalid plugin id: {plugin_id}")
    base = PLUGINS / plugin_id
    manifest = read_json(base / "plugin.json")
    rules = read_json(base / "rules.json")
    if str(manifest.get("id") or "") != plugin_id:
        raise ValueError("plugin.json id mismatch")
    if not manifest.get("version") or not manifest.get("min_core_version"):
        raise ValueError("plugin.json missing version or min_core_version")
    for section in ("matcher", "code_rules", "dedup", "flow"):
        if not isinstance(rules.get(section), dict):
            raise ValueError(f"rules.json missing section: {section}")
    return manifest


def build_zip(plugin_id: str, manifest: dict) -> Path:
    DIST.mkdir(parents=True, exist_ok=True)
    version = str(manifest.get("version") or "").strip()
    out = DIST / f"slowlink-plugin-{plugin_id}-v{version}.zip"
    buf = io.BytesIO()
    base = PLUGINS / plugin_id
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(base.rglob("*")):
            if path.is_file():
                zf.write(path, f"plugins/{plugin_id}/{path.relative_to(base).as_posix()}")
    out.write_bytes(buf.getvalue())
    return out


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin", default="builtin")
    parser.add_argument("--check", action="store_true", help="only validate plugin files")
    args = parser.parse_args()
    manifest = validate_plugin(args.plugin)
    if args.check:
        print(f"ok: {args.plugin} v{manifest.get('version')}")
        return 0
    zipped = build_zip(args.plugin, manifest)
    checksum = DIST / "SHA256SUMS.txt"
    checksum.write_text(f"{sha256(zipped)}  {zipped.name}\n", encoding="utf-8")
    print(zipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
