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
ALLOWED_GENERATOR_STRATEGIES = {"code", "lottery", "line"}


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
    for section in ("matcher", "code_rules", "dedup", "rule_types", "rule_generator", "flow"):
        if not isinstance(rules.get(section), dict):
            raise ValueError(f"rules.json missing section: {section}")
    dynamic_patterns = rules["dedup"].get("dynamic_line_patterns", [])
    if not isinstance(dynamic_patterns, list):
        raise ValueError("dedup.dynamic_line_patterns must be a list")
    for index, pattern in enumerate(dynamic_patterns):
        if not isinstance(pattern, str) or not pattern.strip():
            raise ValueError(f"invalid dynamic line pattern: {index}")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"invalid dynamic line pattern {index}: {exc}") from exc
    code_identity = rules.get("code_identity")
    if code_identity is not None:
        if not isinstance(code_identity, dict):
            raise ValueError("code_identity must be an object")
        mask_char = code_identity.get("mask_char", "*")
        if not isinstance(mask_char, str) or len(mask_char) != 1:
            raise ValueError("code_identity.mask_char must be one character")
        mask_mode = str(code_identity.get("mask_mode") or "any_length")
        if mask_mode not in {"exact", "any_length"}:
            raise ValueError("code_identity.mask_mode must be exact or any_length")
        scope_regex = code_identity.get("scope_regex")
        if not isinstance(scope_regex, str) or not scope_regex.strip():
            raise ValueError("code_identity.scope_regex is required")
        try:
            compiled = re.compile(scope_regex)
        except re.error as exc:
            raise ValueError(f"invalid code_identity.scope_regex: {exc}") from exc
        if not {"scope", "suffix"}.issubset(compiled.groupindex):
            raise ValueError("code_identity.scope_regex requires scope and suffix groups")
        extract_patterns = code_identity.get("extract_patterns", [])
        if not isinstance(extract_patterns, list):
            raise ValueError("code_identity.extract_patterns must be a list")
        for index, pattern in enumerate(extract_patterns):
            if not isinstance(pattern, str) or not pattern.strip():
                raise ValueError(f"invalid code_identity.extract_patterns: {index}")
            try:
                compiled_pattern = re.compile(pattern)
            except re.error as exc:
                raise ValueError(
                    f"invalid code_identity.extract_patterns {index}: {exc}"
                ) from exc
            if "code" not in compiled_pattern.groupindex:
                raise ValueError(
                    f"code_identity.extract_patterns {index} requires code group"
                )
    generator_types = rules["rule_generator"].get("types")
    if not isinstance(generator_types, dict):
        raise ValueError("rule_generator.types must be an object")
    for type_id, item in generator_types.items():
        if not isinstance(item, dict) or not str(item.get("label") or "").strip():
            raise ValueError(f"invalid rule generator type: {type_id}")
        strategy = str(item.get("strategy") or "").strip().lower()
        if strategy not in ALLOWED_GENERATOR_STRATEGIES:
            raise ValueError(f"unsupported generator strategy: {type_id}={strategy}")
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
