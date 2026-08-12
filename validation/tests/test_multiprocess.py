# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from unittest import TestCase

from usd_validation_nvidia import is_multiprocess_safe, multiprocess_safe


class MultiprocessSafeTest(TestCase):
    def test_marks_method_ok(self):
        # Given
        class _Rule:
            @multiprocess_safe
            def CheckLayer(self, layer): ...

        # When / Then
        self.assertTrue(is_multiprocess_safe(_Rule.CheckLayer))

    def test_unmarked_method_nok(self):
        # Given
        class _Rule:
            def CheckLayer(self, layer): ...

        # When / Then
        self.assertFalse(is_multiprocess_safe(_Rule.CheckLayer))
