# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import unittest

from usd_validation_nvidia import (
    BaseRuleChecker,
    CategoryRuleRegistry,
    add_registry_rule_callback,
    register_rule,
)


class TestCategories(unittest.TestCase):

    def test_register_rule_ok(self):
        @register_rule("TestCategory")
        class TestRule(BaseRuleChecker):
            pass

        self.assertIn("TestCategory", CategoryRuleRegistry().categories)
        self.assertIn(TestRule, CategoryRuleRegistry().get_rules("TestCategory"))
        CategoryRuleRegistry().remove(TestRule)

    def test_register_rule_skip_ok(self):
        @register_rule("TestCategory", skip=True)
        class SkippedRule(BaseRuleChecker):
            pass

        self.assertNotIn(SkippedRule, CategoryRuleRegistry().get_rules("TestCategory"))

    def test_register_rule_overwrite_ok(self):
        @register_rule("TestCategory")
        class OldRule(BaseRuleChecker):
            pass

        @register_rule("TestCategory", overwrite=OldRule)
        class NewRule(BaseRuleChecker):
            pass

        self.assertIn("TestCategory", CategoryRuleRegistry().categories)
        self.assertIn(NewRule, CategoryRuleRegistry().get_rules("TestCategory"))
        self.assertNotIn(OldRule, CategoryRuleRegistry().get_rules("TestCategory"))
        CategoryRuleRegistry().remove(NewRule)

    def test_register_rule_callback_ok(self):
        # Test callback is called when rule is registered
        callback = unittest.mock.Mock()

        _subscription = add_registry_rule_callback(callback)

        @register_rule("CallbackCategory")
        class CallbackRule(BaseRuleChecker):
            pass

        callback.assert_called_once()
        CategoryRuleRegistry().remove(CallbackRule)

    def test_register_rule_callback_deregister_ok(self):
        @register_rule("CallbackCategory")
        class CallbackRule(BaseRuleChecker):
            pass

        callback = unittest.mock.Mock()

        _subscription = add_registry_rule_callback(callback)
        CategoryRuleRegistry().remove(CallbackRule)

        callback.assert_called_once()
