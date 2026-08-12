# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest

from usd_validation_nvidia import (
    RulePredicates,
    is_importable,
    should_skip,
    skip_if,
    skip_unless,
)


class ConditionsTestCase(unittest.TestCase):
    def test_is_importable_existing_module(self):
        self.assertTrue(is_importable("importlib")())

    def test_is_importable_reuses_predicate_for_module_name(self):
        self.assertIs(is_importable("importlib"), is_importable("importlib"))

    def test_is_importable_missing_module(self):
        self.assertFalse(is_importable("_usd_validation_nvidia_missing_module_for_test")())

    def test_rule_predicates_is_importable_existing_module(self):
        self.assertTrue(RulePredicates.IsImportable("importlib")())

    def test_rule_predicates_create_bool_condition(self):
        self.assertTrue(RulePredicates.Create(True)())
        self.assertFalse(RulePredicates.Create(False)())

    def test_rule_predicates_create_callable_condition(self):
        predicate = is_importable("importlib")

        self.assertIs(RulePredicates.Create(predicate), predicate)

    def test_rule_predicates_not_condition(self):
        self.assertFalse(RulePredicates.Not(is_importable("importlib"))())
        self.assertTrue(RulePredicates.Not(is_importable("_usd_validation_nvidia_missing_module_for_test"))())

    def test_skip_if_returns_reason_when_condition_is_true(self):
        @skip_if(True, reason="test reason")
        class SkippedRule:
            pass

        self.assertEqual(should_skip(SkippedRule), "test reason")

    def test_skip_if_does_not_skip_when_condition_is_false(self):
        @skip_if(False, reason="test reason")
        class Rule:
            pass

        self.assertIsNone(should_skip(Rule))

    def test_skip_unless_returns_reason_when_condition_is_false(self):
        @skip_unless(False, reason="test reason")
        class SkippedRule:
            pass

        self.assertEqual(should_skip(SkippedRule), "test reason")

    def test_should_skip_returns_first_matching_condition_reason(self):
        @skip_if(True, reason="third reason")
        @skip_if(True, reason="second reason")
        @skip_if(False, reason="first reason")
        class SkippedRule:
            pass

        self.assertEqual(should_skip(SkippedRule), "second reason")

    def test_should_skip_returns_none_when_no_condition_matches(self):
        @skip_if(False, reason="first reason")
        @skip_unless(True, reason="second reason")
        class Rule:
            pass

        self.assertIsNone(should_skip(Rule))

    def test_should_skip_returns_none_for_rule_without_conditions(self):
        class Rule:
            pass

        self.assertIsNone(should_skip(Rule))

    def test_should_skip_catches_predicate_error(self):
        def bad_condition() -> bool:
            raise RuntimeError("test predicate error")

        @skip_if(bad_condition, reason="test reason")
        class SkippedRule:
            pass

        with self.assertLogs("usd_validation_nvidia._conditions", level="ERROR"):
            self.assertEqual(
                should_skip(SkippedRule),
                "Failed to evaluate rule condition: test predicate error",
            )
