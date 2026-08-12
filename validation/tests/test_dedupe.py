# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import unittest
from dataclasses import dataclass

from usd_validation_nvidia.utils import DedupeInfo, DedupeMetaclass


class DedupeMetaclassTests(unittest.TestCase):
    def test_dedupe_info_ok(self):
        @dataclass(frozen=True)
        class Value(metaclass=DedupeMetaclass):
            value: str

        self.assertEqual(
            Value.dedupe_info(),
            DedupeInfo(hits=0, misses=0, maxsize=Value.MAX_DEDUPE_ENTRIES, currsize=0),
        )

        value_a = Value("a")
        value_a_again = Value("a")
        value_b = Value("b")

        self.assertIs(value_a, value_a_again)
        self.assertIsNot(value_a, value_b)
        self.assertEqual(
            Value.dedupe_info(),
            DedupeInfo(hits=1, misses=2, maxsize=Value.MAX_DEDUPE_ENTRIES, currsize=2),
        )

    def test_unhashable_instance_skips_dedupe_ok(self):
        @dataclass(frozen=True)
        class Value(metaclass=DedupeMetaclass):
            values: list[str]

        value_a = Value(["a"])
        value_a_again = Value(["a"])

        self.assertEqual(value_a, value_a_again)
        self.assertIsNot(value_a, value_a_again)
        self.assertEqual(
            Value.dedupe_info(),
            DedupeInfo(hits=0, misses=0, maxsize=Value.MAX_DEDUPE_ENTRIES, currsize=0),
        )

    def test_cache_hit_refreshes_lru_order_ok(self):
        @dataclass(frozen=True)
        class Value(metaclass=DedupeMetaclass):
            value: str

        Value.MAX_DEDUPE_ENTRIES = 2

        value_a = Value("a")
        value_b = Value("b")
        value_a_again = Value("a")
        Value("c")
        value_a_after_eviction = Value("a")
        value_b_after_eviction = Value("b")

        self.assertIs(value_a, value_a_again)
        self.assertIs(value_a, value_a_after_eviction)
        self.assertIsNot(value_b, value_b_after_eviction)
        self.assertEqual(
            Value.dedupe_info(),
            DedupeInfo(hits=2, misses=4, maxsize=Value.MAX_DEDUPE_ENTRIES, currsize=2),
        )
