import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_plugin_hygiene_test",
        ROOT / "scripts" / "build_plugin.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildPluginHygieneTests(unittest.TestCase):
    def test_build_zip_skips_bytecode_cache(self):
        builder = load_builder()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugins = root / "plugins"
            plugin_dir = plugins / "demo"
            plugin_dir.mkdir(parents=True)
            (plugin_dir / "plugin.json").write_text(
                json.dumps({
                    "id": "demo",
                    "name": "Demo",
                    "version": "1.0",
                    "min_core_version": "1.0",
                }),
                encoding="utf-8",
            )
            (plugin_dir / "rules.json").write_text(
                json.dumps({
                    "matcher": {},
                    "code_rules": {},
                    "dedup": {},
                    "flow": {},
                }),
                encoding="utf-8",
            )
            (plugin_dir / "hooks.py").write_text(
                "def echo(payload):\n    return payload\n",
                encoding="utf-8",
            )
            cache = plugin_dir / "__pycache__"
            cache.mkdir()
            (cache / "hooks.cpython-311.pyc").write_bytes(b"stale")
            (plugin_dir / "legacy.pyc").write_bytes(b"stale")

            builder.PLUGINS = plugins
            builder.DIST = root / "dist"
            output = builder.build_zip("demo", {"version": "1.0"})
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()

        self.assertTrue(any(name.endswith("/hooks.py") for name in names))
        self.assertFalse(
            any(
                "__pycache__" in name
                or name.endswith((".pyc", ".pyo"))
                for name in names
            )
        )


if __name__ == "__main__":
    unittest.main()
