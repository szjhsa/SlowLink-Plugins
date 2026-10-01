import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOKS_PATH = ROOT / "plugins" / "builtin" / "hooks.py"


def load_hooks():
    fake_runtime = types.ModuleType("plugin_runtime")
    fake_runtime.load_plugin_module = lambda _name: None
    old_runtime = sys.modules.get("plugin_runtime")
    sys.modules["plugin_runtime"] = fake_runtime
    try:
        spec = importlib.util.spec_from_file_location(
            "builtin_hooks_business_match_test",
            HOOKS_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        if old_runtime is None:
            sys.modules.pop("plugin_runtime", None)
        else:
            sys.modules["plugin_runtime"] = old_runtime


class BuiltinBusinessMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = load_hooks()

    def match(self, text):
        return self.hooks.match_plugin_event(
            {"text": text, "normalized": text, "compact": text}
        )

    def test_scratch_keyword_without_event_fields_does_not_trigger(self):
        for text in (
            "刮刮乐必中体验卡",
            "我是刮刮乐这个",
            (
                "🎮 本群玩法(在群里直接发口令即可)\n\n"
                "🎫 刮刮乐 —— 来张彩票\n"
                "📖 发「比大小规则」「刮刮乐规则」这样的口令看详细玩法"
            ),
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.match(text))

    def test_scratch_event_with_structural_fields_still_triggers(self):
        text = (
            "🎉 刮刮乐\n\n"
            "🎁 奖品：\n"
            "  ▸ 10元代金券 x1\n\n"
            "⏰ 截止时间：2026-10-01 20:00"
        )

        result = self.match(text)

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("matched"))
        self.assertEqual(result.get("rule_type"), "lottery")


if __name__ == "__main__":
    unittest.main()
