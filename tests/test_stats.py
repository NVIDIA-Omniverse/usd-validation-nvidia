# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import enum
import time
import unittest

from nvidia_usd_validation import ValidationStats


class Rule:
    pass


class Severity(enum.Enum):
    FAILURE = enum.auto()


class StatsTests(unittest.IsolatedAsyncioTestCase):
    def test_create_ok(self):
        stats = ValidationStats()

        self.assertEqual(stats.get_rule_times(), [])
        self.assertEqual(stats.get_rule_severity_counts(), [])

    def test_time_rule_sleep_ok(self):
        stats = ValidationStats()

        with stats.time_rule(Rule):
            time.sleep(0.01)

        self.assertEqual(stats.get_rule_times()[0][0], Rule)
        self.assertAlmostEqual(stats.get_rule_times()[0][1], 0.02, delta=0.1)
        self.assertEqual(stats.get_rule_severity_counts(), [])

    def test_time_rule_proc_ok(self):
        stats = ValidationStats()

        with stats.time_rule(Rule):
            total = 0
            for i in range(10):
                total += i

        self.assertEqual(total, 45)
        self.assertEqual(stats.get_rule_times()[0][0], Rule)
        self.assertGreater(stats.get_rule_times()[0][1], 0.0)
        self.assertEqual(stats.get_rule_severity_counts(), [])

    async def test_count_rule_severity_ok(self):
        stats = ValidationStats()
        stats.count_rule_severity(Rule, Severity.FAILURE)

        self.assertEqual(stats.get_rule_times(), [])
        self.assertEqual(stats.get_rule_severity_counts(), [(Rule, Severity.FAILURE, 1)])
