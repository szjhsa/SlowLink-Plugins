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

    def test_instruction_text_does_not_trigger_business_rules(self):
        for text in (
            "刮刮乐必中体验卡",
            "我是刮刮乐这个",
            (
                "🎮 本群玩法(在群里直接发口令即可)\n\n"
                "🎫 刮刮乐 —— 来张彩票\n"
                "📖 发「比大小规则」「刮刮乐规则」这样的口令看详细玩法"
            ),
            "🎉 本群会在每天20点开放注册，具体规则见公告",
            "🃏当前开注状态：True 表示已开放，False 表示已关闭",
            "📝 开放注册中 这几个字是机器人发送的公告标题",
            "本群玩法里的“抽奖信息”是活动卡片提示，不是具体抽奖",
            "当机器人发送「🎁 抽奖开始啦」时，表示抽奖正式开始",
            "群规示例：🍀 祝所有参与者好运！这句话只是祝福语",
            "机器人会在发起了通用抽奖活动后推送卡片",
            "教程：新的抽奖已经创建后会显示参与按钮",
            "教程：🎉 抽奖活动已开始! 是活动卡片标题",
            "功能介绍：机器人会回复“已为您生成了注册码”",
            "教程：新的兑换码已生成后请及时领取",
            "界面说明：出现 🎁 已生成 就代表操作完成",
            "教程：为小虎揍们生成了注册码 是固定提示",
            "群规关键词：虎揍快来",
            "教程：\n虎揍快来",
            "教程：\n📝 开放注册中",
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.match(text))

    def test_structural_event_fields_still_trigger(self):
        samples = (
            (
                "🎉 刮刮乐\n\n"
                "🎁 奖品：\n"
                "  ▸ 10元代金券 x1\n\n"
                "⏰ 截止时间：2026-10-01 20:00",
                "lottery",
            ),
            (
                "🃏当前开注状态：True\n"
                "🎫 总注册限制 | 500\n"
                "🎭 剩余可注册 | 400",
                "keyword",
            ),
        )

        for text, expected_type in samples:
            with self.subTest(text=text):
                result = self.match(text)
                self.assertIsInstance(result, dict)
                self.assertTrue(result.get("matched"))
                self.assertEqual(result.get("rule_type"), expected_type)

    def test_exact_short_lines_still_trigger(self):
        for text in ("📝 开放注册中", "虎揍快来"):
            with self.subTest(text=text):
                result = self.match(text)
                self.assertIsInstance(result, dict)
                self.assertTrue(result.get("matched"))

if __name__ == "__main__":
    unittest.main()
