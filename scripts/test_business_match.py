import importlib.util
import json
import re
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
                result = self.match(text)
                self.assertIsInstance(result, dict)
                self.assertFalse(result.get("matched"))
                self.assertTrue(result.get("suppressed"))

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

    def test_url_identity_and_content_lock_use_separate_namespaces(self):
        code_source = (
            ROOT / "plugins" / "builtin" / "code_rules_impl.py"
        ).read_text(encoding="utf-8-sig")
        storage_source = (
            ROOT / "plugins" / "builtin" / "storage_impl.py"
        ).read_text(encoding="utf-8-sig")

        self.assertIn('(identity or "").partition(":")', code_source)
        self.assertIn('"identity_key_prefix": "dedup:identity:"', storage_source)
        self.assertIn('"dedup:identity:*"', storage_source)

    def test_exhausted_capacity_overrides_open_registration_status(self):
        rules = json.loads(
            (ROOT / "plugins" / "builtin" / "rules.json").read_text(
                encoding="utf-8-sig"
            )
        )
        config = rules["matcher"]
        text = (
            "🃏当前开注状态：True\n"
            "🪢商店开放状态：True\n"
            "🎗️当前允许注册人数：2300\n"
            "🎟️已注册人数：2264\n"
            "🚨被禁用人数：0\n"
            "🎫剩余可注册人数：0"
        )
        compact = re.sub(r"\s+", "", text)

        result = self.hooks.analyze_match_guards(
            {"text": text, "compact": compact, "config": config}
        )

        self.assertTrue(result["closed_register_notice"])

    def test_open_status_with_remaining_capacity_is_not_exhausted(self):
        rules = json.loads(
            (ROOT / "plugins" / "builtin" / "rules.json").read_text(
                encoding="utf-8-sig"
            )
        )
        config = rules["matcher"]
        text = "当前开注状态：True\n剩余可注册人数：36"
        compact = re.sub(r"\s+", "", text)

        result = self.hooks.analyze_match_guards(
            {"text": text, "compact": compact, "config": config}
        )

        self.assertFalse(result["closed_register_notice"])

    def test_lottery_result_message_does_not_trigger(self):
        samples = (
            (
                "到时间啦！！开奖~\n\n"
                "抽奖信息\n"
                "  抽奖 ID：7c7e5526-b5e1-497a-98a0-e5f01a7a732f\n"
                "  创建者：磕巴 白菜\n"
                "  当前参与人数：1345\n\n"
                "中奖信息\n"
                "注册码&续期码 * 5：\n"
                "  ▸ 木 ᶠᵒʳᵉˢᵗ"
            ),
            (
                "🎊 【XP Chat & Gary's Club联合抽奖 · 幸运名单公布】\n"
                "🎁 奖品内容：兑换码 × 10 份\n"
                "👥 总参与：10 位幸运群友诞生\n"
                "🏆 恭喜以下中奖群友：\n"
                "1. @king_GDone"
            ),
        )

        for text in samples:
            with self.subTest(text=text):
                result = self.match(text)
                self.assertIsInstance(result, dict)
                self.assertFalse(result.get("matched"))
                self.assertTrue(result.get("suppressed"))
                self.assertEqual(result.get("reason"), "lottery_result")

    def test_lottery_creation_and_open_event_still_trigger(self):
        samples = (
            (
                "新的抽奖已经创建\n"
                "抽奖信息\n"
                "抽奖 ID：7c7e5526-b5e1-497a-98a0-e5f01a7a732f\n"
                "开奖时间：2026-10-02 20:00"
            ),
            (
                "🎁 抽奖活动已开始！\n"
                "🎁 奖品：\n"
                "  ▸ 月卡 x1\n"
                "⏰ 截止时间：2026-10-02 20:00"
            ),
        )

        for text in samples:
            with self.subTest(text=text):
                result = self.match(text)
                self.assertIsInstance(result, dict)
                self.assertEqual(result.get("rule_type"), "lottery")


if __name__ == "__main__":
    unittest.main()
